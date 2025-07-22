import asyncio
import re
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from utils.logger import logger
from protocols.masxml.parser import is_ping
from protocols.masxml.responses import convert_masxml_ack, convert_masxml_nak
from utils.registry_tools import register_protocol
from protocols.masxml.mode_switcher import MasxmlModeSwitcher
from utils.media_logger import save_base64_media

@register_protocol(Receiver.MASXML)
class MasxmlProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.MASXML)
        self.protocol_mode = mode_manager.get(self.receiver.value)
        self.mode_switcher = MasxmlModeSwitcher(self.protocol_mode)
        self._photo_chunks = {}
        self._recv_buffer = ""

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value, self.mode_switcher),
        )

    async def handle(self, reader, writer, client_ip, client_port, data):
        """Main entry for connection_handler.py; processes incoming data chunk-wise."""
        if isinstance(data, bytes):
            chunk = data.decode(errors="ignore")
        else:
            chunk = data
        self._recv_buffer += chunk

        end_tag = "</XMLMessageClass>"
        while end_tag in self._recv_buffer:
            msg_end = self._recv_buffer.index(end_tag) + len(end_tag)
            full_xml = self._recv_buffer[:msg_end]
            self._recv_buffer = self._recv_buffer[msg_end:]

            await self._handle_xml_message(full_xml, writer, client_ip)

    def get_masxml_label(self, raw_message):
        """Return label for incoming MASXML message (PING, EVENT AJAX, PHOTO, LINK)"""
        # Ping
        if "<MessageType>HEARTBEAT</MessageType>" in raw_message:
            return "PING"
        # Event
        mtype = re.search(r"<MessageType>(\w+)</MessageType>", raw_message)
        event_code = re.search(r"<Key>EventCode</Key><Value>(\w+)</Value>", raw_message)
        if mtype:
            if event_code:
                typ = event_code.group(1)
            else:
                typ = mtype.group(1)

            if "<PacketData>" in raw_message:
                return f"PHOTO {typ}"
            
            if re.search(r"<Key>URL</Key>", raw_message):
                return f"LINK {typ}"
            
            return f"EVENT {typ}"
        # Default
        return "UNKNOWN"

    def get_masxml_response_label(self, response, raw_message):
        """Return label for outgoing MASXML message based on event code and ResultCode."""
        result_code = re.search(r"<ResultCode>(\d+)</ResultCode>", response)
        if result_code:
            code_val = int(result_code.group(1))
            # MASXML: EventCode in <Key>EventCode</Key><Value>CODE</Value>
            event_code = re.search(r"<Key>EventCode</Key><Value>(\w+)</Value>", raw_message)
            if event_code:
                code_label = f"EVENT {event_code.group(1)}"
            elif "<MessageType>HEARTBEAT</MessageType>" in raw_message:
                code_label = "PING"
            else:
                code_label = ""
            if code_val == 0:
                return f"ACK {code_label}".strip()
            else:
                return f"NAK {code_label}".strip()
        return "RESPONSE"

    async def _handle_xml_message(self, raw_message, writer, client_ip):
        mode = self.protocol_mode.mode

        if mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver.value}) NO_RESPONSE mode: skipping reply")
            return

        sequence = re.search(r"<MessageSequenceNo>(\d+)</MessageSequenceNo>", raw_message)
        event_code = re.search(r"<Key>EventCode</Key><Value>(\w+)</Value>", raw_message)
        sequence_num = sequence.group(1) if sequence else "unknown"

        # Mask and save base64 if present
        display_message = raw_message
        payload_match = re.search(r"<Payload>(.*?)</Payload>", raw_message, re.DOTALL)
        if payload_match:
            payload_xml = payload_match.group(1)
            payload_id = re.search(r"<PayloadID>(.*?)</PayloadID>", payload_xml)
            packet_num = re.search(r"<PacketNumber>(\d+)</PacketNumber>", payload_xml)
            file_name_match = re.search(r"<FileName>(.*?)</FileName>", payload_xml)
            last_file = re.search(r"<LastFile>(.*?)</LastFile>", payload_xml)
            b64_data_match = re.search(r"<PacketData>(.*?)</PacketData>", payload_xml, re.DOTALL)

            file_name = file_name_match.group(1) if file_name_match else None
            pkt_num = 0
            try:
                if file_name and isinstance(file_name, str) and len(file_name) > 0:
                    match_index = re.match(r"^(\d+)_", file_name)
                    if match_index:
                        pkt_num = int(match_index.group(1))
                    elif packet_num:
                        pkt_num = int(packet_num.group(1))
                elif packet_num:
                    pkt_num = int(packet_num.group(1))
            except Exception as e:
                logger.error(f"(MASXML) Exception parsing file_name='{file_name}' packet_num='{packet_num}': {e}")
                pkt_num = 0

            if payload_id and b64_data_match:
                pid = payload_id.group(1)
                is_last = last_file and last_file.group(1).lower() == "true"
                b64_data = b64_data_match.group(1)

                if pid not in self._photo_chunks:
                    self._photo_chunks[pid] = {}
                self._photo_chunks[pid][pkt_num] = b64_data

                if is_last:
                    chunks = [self._photo_chunks[pid][i] for i in sorted(self._photo_chunks[pid])]
                    full_b64 = "".join(chunks)
                    img_path = save_base64_media(
                        full_b64,
                        protocol=self.receiver.value,
                        port=self.port,
                        sequence=sequence_num,
                        event_code=event_code.group(1) if event_code else None
                    )
                    logger.info(f"[MASXML MULTIPART PHOTO SAVED]: {img_path}")
                    del self._photo_chunks[pid]


                display_message = raw_message.replace(
                    f"<PacketData>{b64_data}</PacketData>",
                    f"<PacketData>[PHOTO CHUNK, len={len(b64_data)}]</PacketData>"
                )
        else:
            b64_data_match = re.search(r"<PacketData>(.*?)</PacketData>", raw_message, re.DOTALL)
            if b64_data_match:
                b64_data = b64_data_match.group(1)
                img_path = save_base64_media(
                    b64_data,
                    protocol=self.receiver.value,
                    port=self.port,
                    sequence=sequence_num,
                    event_code=event_code.group(1) if event_code else None
                )
                display_message = raw_message.replace(
                    f"<PacketData>{b64_data}</PacketData>",
                    f"<PacketData>[PHOTO BASE64, len={len(b64_data)}]</PacketData>"
                )
                logger.info(f"[MASXML PHOTO SAVED]: {img_path}")

        label_in = self.get_masxml_label(raw_message)
        logger.info(f"({self.receiver.value}) ({client_ip}) <<-- [{label_in}] {display_message.strip()}")

        # Handle ping
        if is_ping(raw_message):
            label_out = "PING"
            if mode == EmulationMode.NAK:
                nak = convert_masxml_nak(
                    raw_message,
                    text="Ping rejected due to emulation mode",
                    code=self.protocol_mode.nak_result_code or 10,
                )
                logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {nak.strip()}")
                writer.write(nak.encode() if isinstance(nak, str) else nak)
            elif mode in [EmulationMode.ONLY_PING, EmulationMode.ACK]:
                ack = convert_masxml_ack(raw_message)
                label_out = self.get_masxml_response_label(ack, raw_message)
                logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {ack.strip()}")
                writer.write(ack.encode() if isinstance(ack, str) else ack)
            else:
                logger.info(f"({self.receiver.value}) ({client_ip}) PING received — skipped due to mode: {mode.value}")
            await writer.drain()
            return

        if mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver.value}) ONLY_PING mode: skipping event")
            return

        if mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver.value}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        if mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver.value}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        # NAK or ACK event
        if mode == EmulationMode.NAK:
            nak = convert_masxml_nak(
                raw_message,
                text="Command rejected due to emulation mode",
                code=self.protocol_mode.nak_result_code or 10,
            )
            label_out = self.get_masxml_response_label(nak, raw_message)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {nak.strip()}")
            writer.write(nak.encode() if isinstance(nak, str) else nak)
        else:
            ack = convert_masxml_ack(raw_message)
            label_out = self.get_masxml_response_label(ack, raw_message)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {ack.strip()}")
            writer.write(ack.encode() if isinstance(ack, str) else ack)

        await writer.drain()
        self.protocol_mode.consume_packet()
