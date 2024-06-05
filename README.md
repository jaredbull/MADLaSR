# MADLaSR

This is Python script used for controlling the MADLaSR device, which was formerly operated using LabVIEW.

This script is able to run an initial test on a reference sample, in addition to running tests for specular and Lambertian reflectivity. 

The drivers required for running the script include [Thorlabs Kinesis](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control) and [Optical Power Monitor (OPM) software](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM). The script relies on specific .dll files from Kinesis and TLPM.py and TLPM.dll files from OPM, ensure the script is calling to the correct location of these files when running the script. The TLPM files should be found in C:\Program Files (x86)\IVI Foundation\VISA\WinNT\TLPM after installing OPM, but the files are also included here to directly download if there are any issues locating them (these may be outdated versions of the files).
