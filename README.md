# SW900 Driver
This is a display driver for the very common SW900 electric vehicle display implemented with a Raspberry Pi Pico (or any other microcontroller) in MicroPython.
We lack some functionality but that can be added in the future (There are big limits, there are only 14 bytes possible we can send, 1 of which is a checksum, so you cant really do much anyway), for now the main functions of the display works.


## Functionality
- Speedometer
- Wattage (Amps are sent, the display makes watts from it itself)
- PAS Level

### Speed
The display calculates speed based of of byte 10 of 13, and the wheel diameter. The calculations are based on a wheel size of 29 Inch (So P06 must be set to 29, else speed cant be set properly). The SW900 has 2 modes of reading speed, one is weird, it involves a bunch of weird shit and 
it limits to 50km/h. I decided not to use that, so P08 must be 50 or over, else it wont work either. We encode the speed into a weird rpm-like thing (idk what it really is but it seems as its a magic number). We divide ```8324``` by the Speed in km/h and then we encode that into hex.

### Wattage
The SW900 has a standard wattage display, the controler sends the current used (In byte 7 of 13), then the display just uses its voltage (Straight battery voltage) to calculate the total power used.

### PAS Level
The display sends the pas level but its split over a full hex bit, we can interpret this tho, and we can use this for other purposes like custom modes or just power levels.

## Workings
The display expects the battery voltage directly, for the correct wattage and battery level to display this must be set in P03. Other than that its pretty chill, it will give error 10 if you dont send data to the display, but it will still function and send data properly. Timings are also easy, you have a 2 to 3 second window to send a packet to the display. The display always sends packets, no matter what.

### The Pipeline
We start by making a UART Connection at 9600 baud, we can just use the pi's default pins, 4 and 5: ```UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))```
For the controler to communicate to the display we only have 1 packet type in the same format possible
A Controler -> Display packet looks like this: 
```
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
```
We do a XOR checksum and add the checksum to the end. This is all the verification it has.
The packet gets checksummed like this: 
```
def make_packet(*b):
    data = bytes(b)
    cs = 0
    for x in data: cs ^= x
    return data + bytes([cs])
```
Then we just send that: ```uart.write(pkt)```
And thats it, the display can function properly now.

There are still some things wrong tho. The ```error``` value for example only has these possible combinations for unique errors
```
# 0x01 = error 7
# 0x02 = error 2
# 0x08 = error 6
# 0x10 = error 9
# 0x20 = error 8
```
The other values (Except current and speed), i have no idea what they do and they dont matter that much anyways.

The SW900 continuously sends updates over the UART bus, its settings can be read and interpreted, but the display uses those itself too, so using them for other purposes isnt really worth it (Espescially since they are sometimes capped to specific values)
So for the best, we only use the PAS level it sends. 
The packet of the display isnt complex but it can sometimes send wrong/corrupted data, hence we verify it.
However first we parse the packet:
```
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
```
This puts the raw data into packets.
We then just use a lookup table for the pas levels and compare them to byte 5.
```
PAS_MAP = {
    0x00: 0,
    0x01: 1,
    0x03: 2,
    0x05: 3,
    0x07: 4,
    0x09: 5,
    0x0b: 6,
    0x0d: 7,
    0x0e: 8,
    0x0f: 9
}
def get_pas(byte_val):
    return PAS_MAP.get(byte_val, -1)
```
To get the PAS level then you can simply loop over packets and do ```get_pas(packet[4])```

Thats all, the SW900 litteraly can't be simpler than this.
