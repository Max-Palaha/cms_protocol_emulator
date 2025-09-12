import asyncio
import re
import logging
from core.connection_handler import BaseProtocol
from utils.constants import Receiver
from utils.mode_manager import mode_manager, EmulationMode
from utils.stdin_listener import stdin_listener
from .parser import (
    parse_microkey_sequence,
    is_ping_microkey,
    build_labels_for_message,
    extract_signals,
    classify_signals,       
    split_complete_frames,
    shrink_media_for_log,   
)
from .responses import generate_ack, generate_nak
from utils.logger import logger
from utils.registry_tools import register_protocol

@register_protocol(Receiver.MICROKEY)
class MicrokeyProtocol(BaseProtocol):
    def __init__(self):
        super().__init__(receiver=Receiver.MICROKEY)
        self.protocol_mode = mode_manager.get(self.receiver.value)
        self._buffers: dict[str, str] = {}

    async def run(self):
        await asyncio.gather(
            super().run(),
            stdin_listener(self.receiver.value),
        )

    async def handle(self, reader, writer, client_ip, client_port, data: bytes):
        # --- Decode incoming bytes to text once ---
        if isinstance(data, bytes):
            try:
                chunk = data.decode("utf-8")
            except UnicodeDecodeError:
                chunk = data.decode("cp1252", errors="replace")
        else:
            chunk = data

        # Accumulate buffer per connection
        key = f"{client_ip}:{client_port}"
        buf = self._buffers.get(key, "") + chunk

        # Extract only COMPLETE frames, keep remainder for next read()
        frames, remainder = split_complete_frames(buf)
        self._buffers[key] = remainder  # save partial tail (if any)

        if not frames:
            # No complete frame yet — wait for more data
            return

        # Process each full frame once
        for frame in frames:
            f = frame.strip()
            if not f:
                continue

            # --- Labeled inbound logging (single source of truth) ---
            label = build_labels_for_message(f)
            label_prefix = (label + " ") if label else ""
            if logger.isEnabledFor(logging.DEBUG):
                display = f.strip()                   
            else:
                display = shrink_media_for_log(f, keep_per_signal=1, max_chars=1200)
            logger.info(f"({self.receiver.value}) ({client_ip}) <<-- {label_prefix}{display}")

            current_mode = self.protocol_mode.mode  # snapshot BEFORE reply

            # NO_RESPONSE: never reply
            if current_mode == EmulationMode.NO_RESPONSE:
                logger.info(f"({self.receiver.value}) NO_RESPONSE mode: skipping reply")
                continue

            # Parse sequence (mandatory)
            sequence = parse_microkey_sequence(f)
            if sequence is None:
                logger.warning(
                    f"({self.receiver.value}) Invalid message format from {client_ip}:{client_port}: {f!r}"
                )
                continue

            # PING branch
            if is_ping_microkey(f):
                if current_mode in [EmulationMode.ONLY_PING, EmulationMode.ACK, EmulationMode.NAK]:
                    pkt = generate_nak(sequence) if current_mode == EmulationMode.NAK else generate_ack(sequence)
                    try:
                        preview = pkt.decode("utf-8").strip()
                    except UnicodeDecodeError:
                        preview = pkt.decode("cp1252", errors="replace").strip()
                    label_word = "NAK" if current_mode == EmulationMode.NAK else "ACK"
                    logger.info(f"({self.receiver.value}) ({client_ip}) -->> [{label_word} PING] {preview}")
                    writer.write(pkt)
                    await writer.drain()
                    self.protocol_mode.consume_packet()
                else:
                    logger.info(
                        f"({self.receiver.value}) ({client_ip}) PING received — skipped due to mode: {current_mode.value}"
                    )
                continue

            # Non-ping traffic in ONLY_PING: skip
            if current_mode == EmulationMode.ONLY_PING:
                logger.info(f"({self.receiver.value}) ONLY_PING mode: skipping event")
                continue

            # DROP_N handling
            if current_mode == EmulationMode.DROP_N and getattr(self.protocol_mode, "drop_count", 0) > 0:
                self.protocol_mode.drop_count -= 1
                logger.info(
                    f"({self.receiver.value}) Dropped message (remaining: {self.protocol_mode.drop_count})"
                )
                if self.protocol_mode.drop_count == 0:
                    # Optionally revert to previous/next mode if your ModeManager supports it
                    self.protocol_mode.set_mode(EmulationMode.ACK)
                continue

            # DELAY_N handling
            if current_mode == EmulationMode.DELAY_N:
                delay = getattr(self.protocol_mode, "delay_seconds", 0)
                if delay:
                    logger.info(f"({self.receiver.value}) Delaying response by {delay}s")
                    await asyncio.sleep(delay)

            # Compose and send reply (ACK/NAK)
            pkt = generate_nak(sequence) if current_mode == EmulationMode.NAK else generate_ack(sequence)
            try:
                preview = pkt.decode("utf-8").strip()
            except UnicodeDecodeError:
                preview = pkt.decode("cp1252", errors="replace").strip()

            # Pretty ACK/NAK label for single-signal frames
            label_word = "NAK" if current_mode == EmulationMode.NAK else "ACK"
            ack_label = ""
            try:
                sigs = extract_signals(f)
                photo_by_code, link_by_code, event_by_code = classify_signals(sigs)

                # pick dominant label if only one category is present
                non_empty = [( "PHOTO", photo_by_code ), ( "LINK", link_by_code ), ( "EVENT", event_by_code )]
                non_empty = [(name, d) for name, d in non_empty if d]

                if len(non_empty) == 1:
                    cat_name, d = non_empty[0]
                    if len(d) == 1:
                        code, count = next(iter(d.items()))
                        suffix = f" x{count}" if count > 1 else ""
                        ack_label = f"[{label_word} {cat_name} {code}{suffix}] "
                    else:
                        # multiple codes within the same category
                        codes = ",".join(d.keys())
                        ack_label = f"[{label_word} {cat_name} {codes}] "
                else:
                    # mixed content frame; keep it short
                    ack_label = f"[{label_word} MIXED] "
            except Exception:
                ack_label = ""

            logger.info(f"({self.receiver.value}) ({client_ip}) -->> {ack_label}{preview}")
            writer.write(pkt)
            await writer.drain()
            self.protocol_mode.consume_packet()

        return
