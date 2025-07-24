import asyncio
import re
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from protocols.sia_dc09.parser import parse_sia_message, is_ping
from protocols.sia_dc09.responses import convert_sia_ack, convert_sia_nak
from utils.logger import logger
from utils.registry_tools import register_protocol

def classify_v_link(link: str) -> str:
    if link.startswith('https://i.ajax.systems/s/'):
        return 'PHOTO'
    if link.startswith('https://ajax-cdn-prod.s3.') or '.jpg' in link or '/image_' in link:
        return 'PHOTO'
    if link.startswith('https://web.ajax.systems'):
        return 'WEB'
    if link.startswith('ajax-pro-desktop://'):
        return 'DESKTOP'
    return 'LINK'

@register_protocol(Receiver.SIA_DCS)
class SIADC09Protocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.SIA_DCS)
        self.protocol_mode = mode_manager.get(self.receiver.value)

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value),
        )

    def get_sia_label(self, message: str) -> str:
        if '"NULL"' in message:
            return "PING"

        if '"SIA-DCS"' in message :
            event_match = re.search(r'"SIA-DCS".*?([A-Z]{2})', message)
            code = event_match.group(1)
            photo_links, web_links, desktop_links, other_links = self.get_link_summary(message)
            if photo_links:
                return f"PHOTO {code} x{len(photo_links)}"
            if web_links:
                return f"WEB_LINK {code}"
            if desktop_links:
                return f"DESKTOP_LINK {code}"
            if other_links:
                return f"LINK {code}"
            return f"EVENT {code}"

        if '"ADM-CID"' in message:
            event_match = re.search(r'\|(\d{4})\s', message)
            code = event_match.group(1) if event_match else None
            photo_links, web_links, desktop_links, other_links = self.get_link_summary(message)
            if photo_links:
                return f"PHOTO {code} x{len(photo_links)}"
            if web_links:
                return f"WEB_LINK {code}"
            if desktop_links:
                return f"DESKTOP_LINK {code}"
            if other_links:
                return f"LINK {code}"
            return f"EVENT {code}"

        return "UNKNOWN"

    def extract_photo_links(self, message: str):
        v_links = re.findall(r'\[V([^\]]+)\]', message)
        photo_links = []
        for v in v_links:
            parts = [part.strip() for part in v.split(',')]
            for part in parts:
                if (
                    part.startswith('https://i.ajax.systems/s/')
                    or part.startswith('https://ajax-cdn-prod.s3.')
                    or '.jpg' in part
                    or '/image_' in part
                ):
                    photo_links.append(part)
        return photo_links

    def get_link_summary(self, message: str):
        v_links = re.findall(r'\[V([^\]]+)\]', message)
        photo_links = []
        web_links = []
        desktop_links = []
        other_links = []
        for v in v_links:
            parts = [part.strip() for part in v.split(',')]
            for part in parts:
                t = classify_v_link(part)
                if t == 'PHOTO':
                    photo_links.append(part)
                elif t == 'WEB' and not web_links:
                    web_links.append(part)
                elif t == 'DESKTOP' and not desktop_links:
                    desktop_links.append(part)
                elif t == 'LINK' and not other_links:
                    other_links.append(part)
        return photo_links, web_links, desktop_links, other_links

    def mask_links_for_log(self, message: str) -> str:
        """
        Leave only the first photo link in each [V...] block, others replaced with [PHOTO_URL], no extra markers.
        """
        def mask_v_block(match):
            v_content = match.group(1)
            parts = [part.strip() for part in v_content.split(',')]
            photo_links = [
                part for part in parts if (
                    part.startswith('https://i.ajax.systems/s/')
                    or part.startswith('https://ajax-cdn-prod.s3.')
                    or '.jpg' in part
                    or '/image_' in part
                )
            ]
            if not photo_links:
                return f"[V{v_content}]"
            masked = []
            seen_photos = 0
            for part in parts:
                if (
                    part.startswith('https://i.ajax.systems/s/')
                    or part.startswith('https://ajax-cdn-prod.s3.')
                    or '.jpg' in part
                    or '/image_' in part
                ):
                    if seen_photos == 0:
                        masked.append(part)
                    else:
                        masked.append(" [PHOTO_URL]")
                    seen_photos += 1
                else:
                    masked.append(part)
            return "[V" + ','.join(masked) + "]"

        masked_message = re.sub(r'\[V([^\]]+)\]', mask_v_block, message)
        return masked_message



    def get_sia_response_label(self, response: str, original_message: str = None) -> str:
        if '"ACK"' in response:
            code = self.get_sia_label(original_message)
            return f"ACK {code}" if code != "UNKNOWN" else "ACK"
        if '"NAK"' in response:
            code = self.get_sia_label(original_message)
            return f"NAK {code}" if code != "UNKNOWN" else "NAK"
        return "RESPONSE"

    async def handle(self, reader, writer, client_ip, client_port, data):

        current_mode = self.protocol_mode.mode

        if current_mode == EmulationMode.NO_RESPONSE:
            logger.info(f"({self.receiver.value}) NO_RESPONSE mode: skipping reply")
            return

        if isinstance(data, bytes):
            message = data.decode(errors="ignore")
        else:
            message = data

        timestamp = self.protocol_mode.get_response_timestamp()
        parsed = parse_sia_message(message)
        if not parsed:
            logger.warning(f"({self.receiver.value}) ({client_ip}) Invalid SIA message: {message.strip()}")
            return

        label_in = self.get_sia_label(message)
        log_message = self.mask_links_for_log(message)
        logger.info(f"({self.receiver.value}) ({client_ip}) <<-- [{label_in}] {log_message.strip()}")

        if is_ping(message):
            if current_mode in [EmulationMode.ONLY_PING, EmulationMode.ACK, EmulationMode.NAK]:
                if current_mode == EmulationMode.NAK:
                    nak = convert_sia_nak(**parsed, timestamp=timestamp)
                    label_out = self.get_sia_response_label(nak, message)
                    logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {nak.strip()}")
                    writer.write(nak.encode() if isinstance(nak, str) else nak)
                else:
                    ack = convert_sia_ack(**parsed, timestamp=timestamp)
                    label_out = self.get_sia_response_label(ack, message)
                    logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {ack.strip()}")
                    writer.write(ack.encode() if isinstance(ack, str) else ack)
                await writer.drain()
            else:
                logger.info(f"({self.receiver.value}) ({client_ip}) PING received — skipped due to mode: {current_mode.value}")
            return

        if current_mode == EmulationMode.ONLY_PING:
            logger.info(f"({self.receiver.value}) ONLY_PING mode: skipping event")
            return

        if current_mode == EmulationMode.DROP_N:
            if self.protocol_mode.drop_count > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(f"({self.receiver.value}) Dropped message (remaining: {self.protocol_mode.drop_count})")
                return
            else:
                self.protocol_mode.set_mode(EmulationMode.ACK)

        if current_mode == EmulationMode.DELAY_N:
            delay = self.protocol_mode.delay_seconds
            logger.info(f"({self.receiver.value}) Delaying response by {delay}s")
            await asyncio.sleep(delay)

        if current_mode == EmulationMode.NAK:
            nak = convert_sia_nak(**parsed, timestamp=timestamp)
            label_out = self.get_sia_response_label(nak, message)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {nak.strip()}")
            writer.write(nak.encode() if isinstance(nak, str) else nak)
        else:
            ack = convert_sia_ack(**parsed, timestamp=timestamp)
            label_out = self.get_sia_response_label(ack, message)
            logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_out}] {ack.strip()}")
            writer.write(ack.encode() if isinstance(ack, str) else ack)

        await writer.drain()
        self.protocol_mode.consume_packet()
