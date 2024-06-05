import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from ctypes import cdll,c_long, c_ulong, c_uint32,byref,create_string_buffer,c_bool,c_char_p,c_int,c_int16,c_double, sizeof, c_voidp
from TLPM import TLPM
import time
from datetime import date
import clr
from System import Decimal

# establishing directories
# edit to your own desired directory
csv_dump = 
plot_dump = 

# establishing constants
# 'ref_test' function can be run to recalibrate the 'intens' variable
intens = 2.92e-5/0.04608 # initial intensity of laser derived from LSRS sample (4.608% reflectivity at 10 degrees)
#intens = 3.05e-5/0.04608
today = str(date.today())
title = None

# importing from Kinesis for travel stages
# ensure to have kinesis drivers installed,
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import *

# connecting/setting up powermeter
tlPM = TLPM() # ensure that the TLPM python library and TLPM DLL are inside same folder containing this script, files included on github
deviceCount = c_uint32()
tlPM.findRsrc(byref(deviceCount))

print("devices found: " + str(deviceCount.value))
print()

resourceName = create_string_buffer(1024)

for i in range(0, deviceCount.value):
    tlPM.getRsrcName(c_int(i), resourceName)
    print(c_char_p(resourceName.raw).value)
    break

tlPM.close()

tlPM = TLPM()
tlPM.open(resourceName, c_bool(True), c_bool(True))

message = create_string_buffer(1024)
tlPM.getCalibrationMsg(message)
print(c_char_p(message.raw).value)
print()

# Set current operating wavelength in nm
wavelength = c_double(633)
tlPM.setWavelength(wavelength)

# Enable auto-range mode.
# 0 -> auto-range disabled
# 1 -> auto-range enabled
tlPM.setPowerAutoRange(c_int16(1))

# Set power unit to Watt.
# 0 -> Watt
# 1 -> dBm
tlPM.setPowerUnit(c_int16(0))

# building device list for travel stages
DeviceManagerCLI.BuildDeviceList()

# serial number for individual travel stages
serial1 = str("45840013")
serial2 = str("45842441")

laser = LongTravelStage.CreateLongTravelStage(serial1)
laser.Connect(serial1)

powermeter = LongTravelStage.CreateLongTravelStage(serial2)
powermeter.Connect(serial2)

# Ensure both devices are connected
if not laser.IsSettingsInitialized() and powermeter.IsSettingsInitialized():
    laser.WaitForSettingsInitialized(10000) # 10 second timeout
    powermeter.WaitForSettingsInitialized(10000)
    assert laser.IsSettingsInitialized() and powermeter.IsSettingsInitialized() is True

# Start polling and enable
laser.StartPolling(250)  # 250ms polling rate
powermeter.StartPolling(250)
time.sleep(10)  # Original set at 25
laser.EnableDevice()
powermeter.EnableDevice()
time.sleep(0.25)  # Wait for device to enable

# Get Device Information and display description
laser_stage_info = laser.GetDeviceInfo()
print('laser travel stage: '+laser_stage_info.Description)
print()
powermeter_stage_info = powermeter.GetDeviceInfo()
print('powermeter travel stage: '+powermeter_stage_info.Description)
print()

motor_config1 = laser.LoadMotorConfiguration(serial1)
motor_config2 = powermeter.LoadMotorConfiguration(serial2)

# Check if devices are homed, home devices if false
print('Travel stages homed:')
if laser.Status.IsHomed and powermeter.Status.IsHomed == True:
    print('Yes')
else:
    print('No')
    print()
    print("Homing Devices")
    laser.Home(180000)  # 120 second timeout
    powermeter.Home(180000)
    print("Done")
    print()

# Get Velocity Params
vel_laser = laser.GetVelocityParams()
vel_laser.MaxVelocity = Decimal(10.0)  # mm/s (Above 10 may be too fast)
laser.SetVelocityParams(vel_laser)
vel_powermeter = powermeter.GetVelocityParams()
vel_powermeter.MaxVelocity = Decimal(10.0)
powermeter.SetVelocityParams(vel_powermeter)

# Laser intensity calibration
# Sets device to take spec reflection measurements of reference sample at 10 deg separation
# Final value is used to calculate total intensity of laser used in 'intens' variable
def ref_test():
    print()
    print('Testing reference sample')
    laser.MoveTo(Decimal(272), 60000)
    powermeter.MoveTo(Decimal(272), 60000)
    time.sleep(1)
    measure = np.array([])
    while len(measure) < 20:
        power = c_double()
        tlPM.measPower(byref(power))
        measure = np.append(measure, ([power.value]))

    avg = np.mean(measure)
    print(f'Measured {avg}')

# Testing specular reflections
def specular():
    print()
    print('Testing specular')
    values = np.array([[],[]])
    df = pd.DataFrame()
    pos = 270 # max 270 min 45
    while pos >= 45:
        laser.MoveTo(Decimal(pos), 60000) # Position value must be a .NET decimal, 60 second timeout
        powermeter.MoveTo(Decimal(pos), 60000)
        time.sleep(0.5)

        # take measurement from powermeter
        measure = np.array([])
        while len(measure) < 10: # Taking 10 measurements at each angle interval
            power = c_double()
            tlPM.measPower(byref(power))
            measure = np.append(measure,([power.value]))

        # average of measurements
        avg = np.mean(measure)

        theta = (2 * np.arctan((294.265 / (pos - 1.735)) - 1)) * (180 / np.pi) # conversion for positions to angle
        values = np.append(values,[[theta],[avg]],1)
        print(f'Measured {avg} at angle {theta}')
        pos -= 5 # increment amount that travel stages move between each measurement (mm)

    # Plotting data
    plt.plot(values[0],values[1]/intens)
    plt.grid()
    plt.title(title+' Specular Reflectivity')
    plt.xlabel('Separation Angle (Degrees)')
    plt.ylabel('Specular Reflectance (Fraction)')
    plt.savefig(plot_dump+title + '_' + today + '_spec.jpeg')
    plt.show()

    # Saving specular data to csv
    df.insert(0,"Angle (Degrees)",values[0],True)
    df.insert(1,"Power (W)",values[1],True)
    df.insert(2,"Specular Reflectance (Measured / Total)",values[1]/intens,True) # measurements divided by intensity of laser as determined by reference sample (intens)
    df.to_csv(csv_dump+title+'_'+today+'_spec.csv',index=False)

# testing lambertian reflections
def lambertian():
    print()
    print('Testing Lambertian')
    values = np.array([[],[]])
    df = pd.DataFrame()
    laser.MoveTo(Decimal(300), 60000)
    pos = 250 # max 250 min 45
    while pos >= 45:
        powermeter.MoveTo(Decimal(pos), 60000)
        time.sleep(0.5)

        # take measurement from powermeter
        measure = np.array([])
        while len(measure) < 10:
            power = c_double()
            tlPM.measPower(byref(power))
            measure = np.append(measure, ([power.value]))

        # average of measurements
        avg = np.mean(measure)

        theta = (np.arctan((294.265 / (pos - 1.735)) - 1)) * (180 / np.pi)
        values = np.append(values, [[theta], [avg]], 1)
        print(f'Measured {avg} at angle {theta}')
        pos -= 5

    # Plotting data
    plt.plot(values[0],values[1]/intens)
    plt.grid()
    plt.title(title+' Lambertian Reflectivity')
    plt.xlabel('Separation Angle (Degrees)')
    plt.ylabel('Lambertian Reflectance (Fraction)')
    plt.savefig(plot_dump+title + '_' + today + '_lamb.jpeg')
    plt.show()

    # Saving lambertian data to csv
    df.insert(0,"Angle (Degrees)",values[0],True)
    df.insert(1,"Power (W)",values[1],True)
    df.insert(2,"Lambertian Reflectance (%)",values[1]/intens,True)
    df.to_csv(csv_dump+title+'_'+today+'_lamb.csv',index=False)

while True:
    print('Type \"ref\" to get a measurement with the LSRS sample, \"spec\" to only run a specular reflection test, '
          '\"lamb\" to only run a\nLambertian reflection test, \"both\" to run both tests for a sammple, or \"quit\" to exit the program.')
    print()
    which_test = input('Enter command: ')

    if which_test == 'ref':
        ref_test()
        print()
    elif which_test == 'spec':
        title = input('Name of sample: ')
        specular()
        print()
    elif which_test == 'lamb':
        title = input('Name of sample: ')
        lambertian()
        print()
    elif which_test == 'both':
        title = input('Name of sample: ')
        specular()
        lambertian()
        print()
    elif which_test == 'quit':
        print()
        print('Exiting program...')
        break
    else:
        print()
        print('Invalid input, try again.')

# reset travel stage positions to zero
laser.MoveTo(Decimal(0), 60000)
powermeter.MoveTo(Decimal(0), 60000)

# disconnecting travel stages
laser.StopPolling()
laser.Disconnect()

powermeter.StopPolling()
powermeter.Disconnect()

# disconnecting powermeter
tlPM.close()

print('Finished')
