from machine import UART, Pin
import time

uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))

def get_pas(byte_val):
    return PAS_MAP.get(byte_val, -1)
def make_packet(*b):
    data = bytes(b)
    cs = 0
    for x in data: cs ^= x
    return data + bytes([cs])

def parse_packets(data):
    packets = []
    i = 0
    while i < len(data) - 19:
        if data[i] == 0x01:
            pkt = data[i:i+20]
            cs = 0
            for b in pkt[:19]: cs ^= b
            if cs == pkt[19]:
                if (pkt[1] == 0x14 and 
                    pkt[2] == 0x01 and 
                    pkt[5] == 0x80 and 
                    pkt[6] == 0x2e):
                    packets.append(pkt)
                    i += 20
                    continue
        i += 1
    return packets
def speed_to_bytes(kmh):
    if kmh <= 0:
        return 0x3a, 0x98
    raw = round(8324 / kmh)
    raw = max(1, min(255, raw))
    return raw, 0x00
def current_to_bytes(amps):
    return max(0, min(255, amps))
# 0x01 = error 7
# 0x02 = error 2
# 0x08 = error 6
# 0x10 = error 9
# 0x20 = error 8

# All possible error codes, there could be more in other bits, but from 0x00 to 0xFF this is all.
def send(kmh=0, error=0x00, current=0):
    speed_raw, speed_mode = speed_to_bytes(kmh)
    current_raw = current_to_bytes(current)
    pkt = make_packet(
        0x02, 0x0e, 0x01,
        error,
        0x10,
        0x00,
        current_raw,
        0x00,
        speed_mode,
        speed_raw,
        0x00,
        0x00,
        0x00
    )
    uart.write(pkt)

while True:
    send(kmh=0, error=0x00, current=0)
    time.sleep_ms(100)
    if uart.any():
        raw = uart.read(uart.any())
        packets = parse_packets(raw)
        for p in packets:
            print(f"PAS: {get_pas(p[4])}")
    time.sleep_ms(96)

