#write_to_file(filename, "\nUsing user-input PLC definitions from \'FMB_PLCs.py\'")
if plc_num == 6:
	#write_to_file(filename, "\nPLC6 enabled")
	self.set_p_var(86, 1)	#StartupStarted
	self.set_p_var(95, 0)	#ShutdownNotCompleted
	sleep(2)				#DrivePhasing takes some time
	self.set_p_var((self.caxis*100 + 17), 1)	#DrivePhased
	self.set_p_var(96, 1)	#AutoStartupCompleted
	self.set_p_var(86, 0)	#StartupNotStarted
#elif plc_num == 12:
if plc_num == 12:
	#write_to_file(filename, "\nPLC12 enabled")
	self.set_p_var(196, 1)	#ShutdownStarted
	self.set_p_var(96, 0)	#AutoStartupNotCompleted
	self.set_p_var((self.caxis*100 + 17), 0)	#DriveNotPhased
	self.set_p_var(95, 1)	#ShutdownCompleted
	self.set_p_var(196, 0)	#ShutdownNotStarted
#elif 0<=plc_num<=31:
	#write_to_file(filename, "\nenabling of PLC%r requested, but no such PLC program exists"%(plc_num))
#else:
	#write_to_file(filename, "\nenabling of PLC%r requested, but no such PLC program exists as PLC number out of bounds"%(plc_num))
