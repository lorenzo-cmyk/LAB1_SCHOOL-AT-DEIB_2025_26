package main

import (
	"crypto/rand"
	"encoding/binary"
	"fmt"
	"log"
	"net"
	"sync"
	"syscall"
	"time"
)

const (
	ttlThreshold = 100
	listenPort   = 2000
	ethPAll      = 0x0003
)

var (
	ttlMap   = make(map[string]int)
	ttlMapMu sync.Mutex
)

func main() {
	ifaces, err := net.Interfaces()
	if err != nil {
		log.Fatalf("interfaces: %v", err)
	}
	snifferCount := 0
	for _, iface := range ifaces {
		if iface.Flags&net.FlagUp == 0 {
			continue
		}
		go sniffOnInterface(iface.Index, iface.Name)
		snifferCount++
	}
	if snifferCount == 0 {
		log.Fatal("no network interfaces found for packet capture (need root/CAP_NET_RAW)")
	}

	fd, err := syscall.Socket(syscall.AF_INET, syscall.SOCK_STREAM, 0)
	if err != nil {
		log.Fatalf("socket: %v", err)
	}
	defer syscall.Close(fd)

	if err := syscall.SetsockoptInt(fd, syscall.SOL_SOCKET, syscall.SO_REUSEADDR, 1); err != nil {
		log.Fatalf("SO_REUSEADDR: %v", err)
	}

	if err := syscall.Bind(fd, &syscall.SockaddrInet4{Port: listenPort}); err != nil {
		log.Fatalf("bind: %v", err)
	}
	if err := syscall.Listen(fd, 128); err != nil {
		log.Fatalf("listen: %v", err)
	}

	time.Sleep(100 * time.Millisecond)
	log.Printf("listening on :%d (TTL threshold: %d)", listenPort, ttlThreshold)

	for {
		connFd, sa, err := syscall.Accept(fd)
		if err != nil {
			log.Printf("accept: %v", err)
			continue
		}
		var clientIP string
		var clientPort int
		if addr, ok := sa.(*syscall.SockaddrInet4); ok {
			clientIP = net.IP(addr.Addr[:]).String()
			clientPort = addr.Port
		}
		go handle(connFd, clientIP, clientPort)
	}
}

func handle(fd int, clientIP string, clientPort int) {
	defer syscall.Close(fd)

	key := fmt.Sprintf("%s:%d", clientIP, clientPort)

	ttlMapMu.Lock()
	ttl, found := ttlMap[key]
	if found {
		delete(ttlMap, key)
	}
	ttlMapMu.Unlock()

	buf := make([]byte, 4096)
	syscall.Read(fd, buf)

	if !found {
		log.Printf("rejected %s (no SYN TTL recorded)", key)
		deny(fd)
		return
	}

	if ttl < ttlThreshold {
		log.Printf("rejected %s (TTL %d < %d)", key, ttl, ttlThreshold)
		deny(fd)
		return
	}

	payload := randomASCII(13) + "TTL"
	resp := fmt.Sprintf("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s", len(payload), payload)
	syscall.Write(fd, []byte(resp))

	log.Printf("served %s (TTL %d)", key, ttl)
}

func deny(fd int) {
	body := "ACCESS_DENIED"
	resp := fmt.Sprintf("HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s", len(body), body)
	syscall.Write(fd, []byte(resp))
}

func sniffOnInterface(ifIndex int, ifName string) {
	fd, err := syscall.Socket(syscall.AF_PACKET, syscall.SOCK_RAW, int(htons(ethPAll)))
	if err != nil {
		log.Printf("sniffer on %s: %v (need root/CAP_NET_RAW)", ifName, err)
		return
	}
	defer syscall.Close(fd)

	addr := syscall.SockaddrLinklayer{
		Protocol: htons(ethPAll),
		Ifindex:  ifIndex,
	}
	if err := syscall.Bind(fd, &addr); err != nil {
		log.Printf("bind to %s: %v", ifName, err)
		return
	}

	buf := make([]byte, 65535)
	for {
		n, _, err := syscall.Recvfrom(fd, buf, 0)
		if err != nil {
			continue
		}
		parsePacket(buf[:n])
	}
}

func parsePacket(pkt []byte) {
	if len(pkt) < 14+20+20 {
		return
	}

	ethType := binary.BigEndian.Uint16(pkt[12:14])
	if ethType != 0x0800 {
		return
	}

	ip := pkt[14:]
	ihl := int(ip[0]&0x0F) * 4
	if ihl < 20 || len(pkt) < 14+ihl+20 {
		return
	}
	if ip[9] != syscall.IPPROTO_TCP {
		return
	}

	ttl := int(ip[8])
	srcIP := net.IP(ip[12:16]).String()
	srcPort := int(binary.BigEndian.Uint16(ip[ihl : ihl+2]))
	dstPort := int(binary.BigEndian.Uint16(ip[ihl+2 : ihl+4]))
	flags := ip[ihl+13]

	syn := flags&0x02 != 0
	ack := flags&0x10 != 0

	if syn && !ack && dstPort == listenPort {
		key := fmt.Sprintf("%s:%d", srcIP, srcPort)
		ttlMapMu.Lock()
		ttlMap[key] = ttl
		ttlMapMu.Unlock()
	}
}

func htons(v uint16) uint16 {
	return (v << 8) | (v >> 8)
}

func randomASCII(n int) string {
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	for i := range b {
		b[i] = 33 + b[i]%94
	}
	return string(b)
}
