
# LENSS 5G-Transport-Converter

## What is the LENSS 5G-Transport-Converter?
The LENSS 5G-Transport-Converter is the first widely available open source Transport Converter for 5G core networks. It allows you to use the ATSSS protocol along with our modified version of Tessares's [libconvert](https://github.com/Tessares/libconvert) to create multi-access PDU (MA-PDU) sessions over both 3GPP and non-3GPP access networks concurrently. 

## How does it work?
Our Transport Converter is a split TCP connection proxy which takes an incoming MPTCP session and proxies it to a destination server as TCP traffic. This allows you to utilize multiple access networks concurrently and utilize maximum bandwidth despite the overall low adoption of MPTCP accross the web. 
```
                 MPTCP
--------------  subflow
| 3GPP iface | ------->|     (Terminate MPTCP) -> (TCP)
--------------	       |       -----------------------
                       |------>| Transport Converter  |--->{Internet Server}			
--------------	       |       ----------------------- TCP
| WiFi iface | ------->|
--------------  MPTCP 
              subflow
```

## What is libconvert?
Tessares's libconvert is the first open source client library to support the 0-RTT transport protocol as specified in RFC 8803, which has been standardized by 3GPP to be the driving transport protocol underlying ATSSS. We have modified libconvert to work with our Transport Converter in order to provide end-to-end support for multi-access data sessions.

## Installation
1. Clone the repository.
```
https://github.com/LENSS/5G-Transport-Converter.git
cd 5G-Transport-Converter
```
2. Build libconvert client.
```
make lib_convert.so
```
3. Setup the Transport Converter.
```
make setup_transport_converter
```

## Running
1. Set TCP Fast Open:
```
sysctl -w net.ipv4.tcp_fastopen=5
```
2. Run the Transport  Converter
```
make run_transport_converter
```
Note: You will need to configure the IP and port that the Transport Converter will run on in `5GTC/config.yaml`.

3. Run arbitrary C code that utilizes MPTCP sockets using libconvert.
```
LD_PRELOAD=libconvert.so CONVERT_ADDR=[IP of Transport Converter] CONVERT_PORT=[Port of Transport Converter] ./code arg1 arg2 ... argn
```

## Client Utility
We have provided a client utility for measuring network performance using our Transport Converter. It can be found in `/5GTC/evaulation/mptcp_client.c`.
In the `/5GTC/evaulation` directory, run `make`.

This will create a binary `mptcp_client` which can be run as follows:
```
mptcp_client <local IP> <server IP> <server port> [buffer size] [--uplink | --downlink] [--download-size <bytes>] [--upload-size <bytes>]
```
The client can be used in uplink exclusive (ie. send data only), downlink (ie. read data only) or echo (ie. read and write back data) modes. The client is configured to be used with our provided server located in the same directory:

```
python mptcp_server.py
```
Note: While our server uses MPTCP, this is purely to allows you to use the client and server pair with or without the Transport Converter. If the Transport Converter proxies traffic for the client, the server will default to use a standard TCP connection.

The client and server exchange a unique packet in order to configure the session. This packet is created based on the command line options you use to run the client.

## Web UI
The Transport Converter includes a web interface that is generated for each active session, allowing you to view subflow performance in real time.
After you have started a transport session, you will see a unique ID printed in the terminal session where your Transport Converter is running. Navigate to the address and port you configured for the Web UI in `/5GTC/config.yaml` with the unique session ID:
```
http://[WEBUI_HOST:[WEBUIPORT]/[SESSION_ID]
```
You will see live graphs showing the active performance of each subflow created between the client and Transport Converter.

Note: Configure your machine to create subflows on chosen network interface using the built in [ip-mptcp](https://man7.org/linux/man-pages/man8/ip-mptcp.8.html) command.
