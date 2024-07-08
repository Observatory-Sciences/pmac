logging.debug("Using default PLC definitions from \'defaultPLCs.py\'")
write_to_file(filename, "\nUsing default PLC definitions from \'defaultPLCs.py\'")
if 0<=plc_num<=31:
	logging.debug("Enabling of PLC{} requested, but no such PLC program exists".format(plc_num))
else:
	logging.debug("Enabling of PLC{} requested, but no such PLC program exists as PLC number out of b ounds".format(plc_num))
