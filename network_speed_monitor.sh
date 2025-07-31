#!/bin/sh /etc/rc.common
# Copyright (C) 2025 OpenWrt.org

START=95
STOP=15

USE_PROCD=1

SERVICE_DAEMONIZE=1
SERVICE_WRITE_PID=1

PROG=/usr/bin/python3
SCRIPT=/root/network_speed_monitor.py

start_service() {
    procd_open_instance
    procd_set_param command "$PROG" "$SCRIPT"
    procd_set_param stdout 1
    procd_set_param stderr 1
    procd_set_param respawn
    procd_close_instance
}

stop_service() {
    ps | grep "$SCRIPT" | grep "$PROG" | awk '{print $1}' | xargs kill -9
}