from driver_inversor_cfw11 import Inverter
import time

from init_serial_devices import selecionar_porta

inversor_motor = Inverter(Port=selecionar_porta("Inversor"), ADR=1, Baudrate=57600, Timeout=0.001)

inversor_motor.SendReferenceAngularVelocity(20)
time.sleep(1)
inversor_motor.StopMotor()

