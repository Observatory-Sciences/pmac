import sys
import threading
from time import sleep
import time
import logging
import SocketServer
import npyscreen
import datetime #Elena added for debugging
import ply.lex as lex #Elena added

current_milli_time = lambda: int(round(time.time() * 1000))

# Trajectory scanning M variable definitions
M_TRAJ_STATUS = 4034
M_TRAJ_VERSION = 4049
M_TRAJ_BUFSIZE = 4037
M_TRAJ_A_ADR = 4041
M_TRAJ_B_ADR = 4042
M_TRAJ_TOTAL_PTS = 4038
M_TRAJ_C_INDEX = 4039
M_TRAJ_C_BUF = 4040
M_TRAJ_BUF_FILL_A = 4044
M_TRAJ_BUF_FILL_B = 4045

#Elena adding write to file function:
#def write_to_file(filename, text):
#	'''
#	Takes filename, and text to be written to that file
#	If text is a tuple, it will write a string of each element to the file
#	If text is a single item, it will write a string of the item to the file
#	'''
#	f = open(filename, "a")
#	if isinstance(text, tuple):
#	    for item in text:
#	        f.write(str(item))
#	else:
#	    f.write(str(text))
#	f.close()

class SimulatedPmacAppGui(npyscreen.NPSAppManaged):
    def __init__(self):
        super(SimulatedPmacAppGui, self).__init__()
        self.pmac_thread = PmacThread()

    def get_status(self):
        values = []
        axes = self.pmac_thread.simulator.axes
        values.append("Axis 1 : " + str(axes[1].readPosition()))
        values.append("Axis 2 : " + str(axes[2].readPosition()))
        values.append("Axis 3 : " + str(axes[3].readPosition()))
        values.append("Axis 4 : " + str(axes[4].readPosition()))
        values.append("Axis 5 : " + str(axes[5].readPosition()))
        values.append("Axis 6 : " + str(axes[6].readPosition()))
        values.append("Axis 7 : " + str(axes[7].readPosition()))
        values.append("Axis 8 : " + str(axes[8].readPosition()))
        return values

    def create_pmac(self, port, plc_file):
        self.pmac_thread.create_pmac(port, plc_file)

    def onStart(self):
        self.keypress_timeout_default = 100
        self.registerForm("MAIN", IntroForm())
        self.registerForm("MAIN_MENU", MainMenu())

class SimulatedPmacAppNoGui():
    def __init__(self, tcp_port, plc_file = 'defaultPLCs.py'):
        self.port = tcp_port
        self.plc_file = plc_file
        self.pmac_thread = PmacThread()

    def run(self):
        print 'launching headless pmac simulator on port', self.port
        print 'using plc definition file', self.plc_file
        self.pmac_thread.create_pmac(self.port, self.plc_file)
        while True:
            threading._sleep(.1)


class PmacThread():
    def __init__(self):
        self.server = None
        self.simulator = None
        self.server_thread = None

    def create_pmac(self, port, plc_file):
        # Create the simulator
        self.simulator = PMACSimulator(plc_file)
        # Start the simulator thread
        self.simulator_thread = threading.Thread(target=self.update)
        self.simulator_thread.daemon = True
        self.simulator_thread.start()
        # Setup the server
        HOST, PORT = "localhost", int(port)
        self.server = PMACServer((HOST, PORT), MyTCPHandler, simulator=self.simulator)
        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        # Exit the server thread when the main thread terminates
        self.server_thread.daemon = True
        self.server_thread.start()

    def update(self):
        while self.simulator.getRunning():
            self.simulator.update()
            sleep(0.001)


class IntroForm(npyscreen.Form):
    def create(self):
        self.name = "Simulated PMAC"
        self.add(npyscreen.TitleText, labelColor="LABELBOLD", name="Set the port number for the simulator", value="",
                 editable=False)
        self.port = self.add(npyscreen.TitleText, name="Port Number: ", value="1025")
        self.add(npyscreen.TitleText, labelColor="LABELBOLD", name="Set the filename for the file containing the PLCs to be used by the simulator", value="",
                 editable=False)
        self.plc_file = self.add(npyscreen.TitleText, name="File: ", value="defaultPLCs.py")

    def afterEditing(self):
        self.parentApp.create_pmac(int(self.port.value), self.plc_file.value)
        self.parentApp.setNextForm("MAIN_MENU")


class MainMenu(npyscreen.FormBaseNew):
    def create(self):
        self.keypress_timeout = 1
        self.name = "Simulated PMAC"
        self.t2 = self.add(npyscreen.BoxTitle, name="Main Menu:", relx=2, max_width=24)  # , max_height=20)
        self.t3 = self.add(npyscreen.BoxTitle, name="Current Status:", rely=2,
                           relx=26)  # , max_width=45, max_height=20)

        self.t2.values = ["Exit"]
        self.t2.when_value_edited = self.button

    def while_waiting(self):
        #self.parentApp.update()
        self.t3.values = self.parentApp.get_status()
        self.t3.display()

    def button(self):
        selected = self.t2.entry_widget.value
        if selected == 0:
            self.parentApp.setNextForm(None)
            self.parentApp.switchFormNow()


class PMACServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, simulator=False):
        self.simulator = simulator
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=bind_and_activate)


class MyTCPHandler(SocketServer.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        while 1:
            # self.request is the TCP socket connected to the client
            self.data = self.request.recv(1024)  # .strip()
            #write_to_file(filename, ("\nIn handle function, self.data = self.request.recv(1024) = ", repr(self.data)))
            if not self.data:
                #write_to_file(filename, "\nbreaking out of handle function")
                break
                #continue #Elena trying stuff
            # First 8 bytes are packet header
            header = self.data[0:8]
            message = self.data[8:]

            logging.debug("Request: %s", message)
            #write_to_file(filename, ("\nRequest:", repr(message)))
            response = self.server.simulator.parse(message)
            logging.debug("Response: %s", response.replace('\r', '\\r'))
            #write_to_file(filename, ("\nResponse:", repr(response)))
            resp_to_print = response + '\6'
            self.request.sendall(response + '\6')


class PMACAxis():
    def __init__(self):
        self.ivars = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 10000, -10000, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 50, 50, 50, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.position = 0.0
        self.dmd_position = 0.0
        self.velocity = 20
        self.done = 1
        self.amp_enabled = 0
        self.lolimhit = False
        self.hilimhit = False

    def getStatus(self):
        #return "88000080040" + self.done
        #first_char_binary = 1*1000 + self.lolimhit*100 + self.hilimhit*10 + 0*1
        #first_char_binary = 0b1001 | self.lolimhit<<2 | self.hilimhit<<1
        #first_char_decimal = int(str(first_char_binary),2)
        #first_char_hex = hex(first_char_decimal)
        #first_char_hex = hex(first_char_binary)
        #status_hex = 0x9880000018400 | self.lolimhit<<46 | self.hilimhit<<45 | self.done<<0
        status_hex = 0x800000018400 | self.amp_enabled<<43 | self.lolimhit<<46 | self.hilimhit<<45 | self.done<<0
        #status_str = str(status_hex[-1].upper())
        return '{:02X}'.format(status_hex)
        #return first_char + "8000001840" + self.done
        #return "88000001840" + self.done

    def writeIVar(self, no, value):
        self.ivars[no] = value

    def readIVar(self, no):
        return self.ivars[no]

    def readPosition(self):
        return self.position

    def move(self, position):
        lolim = self.ivars[14]
        hilim = self.ivars[13]
        self.amp_enabled = 1
        if position > lolim and position < hilim:
            self.dmd_position = position
        if position <= lolim:
            self.dmd_position = lolim
        if position >= hilim:
            self.dmd_position = hilim

    def stop(self):
        self.amp_enabled = 1
        self.dmd_position = self.position

    def update(self):
        # print "position: " + str(self.position)
        # print "dmd_position: " + str(self.dmd_position)
        self.velocity = self.ivars[22]
        #self.velocity = 20 #Elena add just to check if velocity=0 is what's breaking stuff
        #write_to_file(filename, ("\nposition: ", str(self.position), ", dmd_position: ", str(self.dmd_position),", velocity: ", repr(self.velocity)))
        #write_to_file(filename, "\nUpdating axis position")
        if self.position == self.ivars[14]: #lolim
            self.lolimhit = True
        else:
            self.lolimhit = False
        if self.position == self.ivars[13]: #hilim
            self.hilimhit = True
        else:
            self.hilimhit = False
        if self.position < (self.dmd_position - self.velocity):
            self.position = self.position + self.velocity
            self.done = 0
        elif self.position > (self.dmd_position + self.velocity):
            self.position = self.position - self.velocity
            self.done = 0
        else:
            self.position = self.dmd_position
            self.done = 1

class CoordinateSystem():
    def __init__(self, controller):
        self.controller = controller
        self.in_position = 1
        self.running_scan = False
        self.time_at_last_point = 0.0
        self.delta_time = 0
        self.motion_prog = 0.0

    def run_program(self):
        logging.debug("Running motion program")
        #write_to_file(filename, "\nRunning motion programme")
        self.in_position = 0
        self.controller.set_m_var(M_TRAJ_STATUS, 1)  # Set status to active
        self.controller.set_m_var(M_TRAJ_TOTAL_PTS, 0)  # total points
        self.controller.set_m_var(M_TRAJ_C_INDEX, 0)  # current index
        self.controller.set_m_var(M_TRAJ_C_BUF, 0)  # current buffer
        self.time_at_last_point = current_milli_time()
        buffer_memory_address = self.controller.get_m_var(M_TRAJ_A_ADR)
        self.delta_time = (self.controller.read_memory_address(buffer_memory_address)&0xFFFFFF) / 1000
        #write_to_file(filename, ("\nself.delta_time = ", self.delta_time))
        logging.debug("self.delta_time: %f", self.delta_time)
        for axis in range(1, 9):
            position_memory_address = buffer_memory_address + (1000 * axis)
            current_position = self.controller.axes[axis].readPosition()
            new_position = self.controller.read_position(position_memory_address)
            if self.delta_time == 0:
                logging.debug("Zero delta time for CS")
                #write_to_file(filename, "\nZero delta time for CS")
                velocity = 1.0
            else:
                velocity = (new_position - current_position) / self.delta_time
            if velocity < 0.0:
                velocity *= -1.0
            #write_to_file(filename, ("\nVelocity set to ", velocity))
            self.controller.axes[axis].writeIVar(22, velocity)
            self.controller.axes[axis].move(float(new_position))
        self.running_scan = True

    def update(self):
        # Check if we are running the trajectory scan
        #write_to_file(filename, "\nChecking if we are running the trajectory scan")
        if self.running_scan:
            #write_to_file(filename, "\nself.running_scan = True")
            # Check for an abort
            status = self.controller.get_m_var(M_TRAJ_STATUS)  # Set status to active
            #write_to_file(filename, ("\nStatus = ", status))
            if status != 1:
                # Aborted to stop the scan
                #write_to_file(filename, "\nAbort to stop trajectory scan")
                self.running_scan = False
                self.in_position = 1
            else:
                # Read the current time
                current_time = current_milli_time()
                # Read the time for last point
                # Work out if we should be moving to the next point
                if current_time > (self.time_at_last_point + self.delta_time):
                    # Get the point
                    point_index = self.controller.get_m_var(M_TRAJ_C_INDEX)
                    # increment the point
                    point_index = point_index + 1
                    # Check to see if we have crossed buffer
                    if point_index == self.controller.get_m_var(M_TRAJ_BUFSIZE):
                        point_index = 0
                        if self.controller.get_m_var(M_TRAJ_C_BUF) == 0:
                            self.controller.set_m_var(M_TRAJ_C_BUF, 1)
                            self.controller.set_m_var(M_TRAJ_BUF_FILL_A, 0)
                        else:
                            self.controller.set_m_var(M_TRAJ_C_BUF, 0)
                            self.controller.set_m_var(M_TRAJ_BUF_FILL_B, 0)

                    # Read the buffer A or B
                    current_buffer = self.controller.get_m_var(M_TRAJ_C_BUF)
                    if current_buffer == 0:
                        # We are in buffer A
                        current_buffer_fill = M_TRAJ_BUF_FILL_A
                        current_buffer_address = M_TRAJ_A_ADR
                    else:
                        # We are in buffer B
                        current_buffer_fill = M_TRAJ_BUF_FILL_B
                        current_buffer_address = M_TRAJ_B_ADR

                    # Set the new point index
                    self.controller.set_m_var(M_TRAJ_C_INDEX, point_index)
                    # Increment the total points
                    total_points = self.controller.get_m_var(M_TRAJ_TOTAL_PTS)+1
                    self.controller.set_m_var(M_TRAJ_TOTAL_PTS, total_points)
                    logging.debug("Total points: %d", total_points)
                    if point_index == self.controller.get_m_var(current_buffer_fill):
                        # Scan has finished, we caught up
                        self.running_scan = False
                        self.in_position = 1
                        self.controller.set_m_var(M_TRAJ_STATUS, 2)  # Set status to IDLE
                    else:
                        # Work out delta time
                        buffer_memory_address = self.controller.get_m_var(current_buffer_address) + point_index
                        self.delta_time = (self.controller.read_memory_address(buffer_memory_address)&0xFFFFFF) / 1000
                        #write_to_file(filename, ("\nself.delta_time = ", self.delta_time))
                        self.time_at_last_point = current_time
                        for axis in range(1,9):
                            position_memory_address = buffer_memory_address + (1000*axis)
                            current_position = self.controller.axes[axis].readPosition()
                            new_position = self.controller.read_position(position_memory_address)
                            if self.delta_time == 0:
                                logging.debug("Zero delta time for CS")
                                #write_to_file(filename, "\nZero delta time for CS")
                                velocity = 1.0
                            else:
                                velocity = (new_position - current_position) / self.delta_time
                            if velocity < 0.0:
                                velocity *= -1.0
                            #write_to_file(filename, ("\nVelocity = ", velocity))
                            self.controller.axes[axis].writeIVar(22, velocity)
                            self.controller.axes[axis].move(float(new_position))

                        logging.debug("Reading trajectory time: %d", self.delta_time)

                    # Work out the velocity
                    # Set the move demands
                    # Update the counters


    def get_status(self):
        logging.debug("Status requested: %d", self.in_position)
        #write_to_file(filename, ("\nStatus requested: ", self.in_position))
        if self.in_position == 1:
            return "000000020000000000"
        else:
            return "000005000010000000"

class PMACSimulator():
    def __init__(self, plc_file):
        # print "init called"
        self.running = True
        self.plc_file = plc_file
        self.ivars = {}
        self.pvars = [0] * 16000
        self.mvars = [0] * 16000
        self.memory = [0] * 1000000
        self.caxis = 1
        self.ccs = 1
        self.inhash = False
        self.inival = False
        self.sval = ""
        self.lastMessage = ""
        self.lastResponse = ""
        self.axes = {1: PMACAxis(),
                     2: PMACAxis(),
                     3: PMACAxis(),
                     4: PMACAxis(),
                     5: PMACAxis(),
                     6: PMACAxis(),
                     7: PMACAxis(),
                     8: PMACAxis()}
        self.cs = {1: CoordinateSystem(self),
                   2: CoordinateSystem(self),
                   3: CoordinateSystem(self),
                   4: CoordinateSystem(self),
                   5: CoordinateSystem(self),
                   6: CoordinateSystem(self),
                   7: CoordinateSystem(self),
                   8: CoordinateSystem(self),
                   9: CoordinateSystem(self),
                   10: CoordinateSystem(self),
                   11: CoordinateSystem(self),
                   12: CoordinateSystem(self),
                   13: CoordinateSystem(self),
                   14: CoordinateSystem(self),
                   15: CoordinateSystem(self),
                   16: CoordinateSystem(self)}
        # print self.axes
        self.setup_trajectory_interface()
        self.setup_some_standard_mvars()
        # write datetime to file when first called
        now = datetime.datetime.now()
        global filename
        filename = "test/test_" + now.strftime("%d%m%y_%H%M%S") + ".txt"
        #write_to_file(filename, ("\nInitiating Simulator at ", now.strftime("%d/%m/%Y %H:%M:%S")))
        #f = open(filename, "a")
		#f.write("\nInitiating Simulator at ")
		#f.write(now.strftime("%d/%m/%Y %H:%M:%S"))
		#f.close()

    def setup_some_standard_mvars(self):
        # pmac interupt timings (for processor timing calcs)
        self.mvars[70] = 11990
        self.mvars[71] = 554
        self.mvars[72] = 2621
        self.mvars[73] = 76

    def setup_trajectory_interface(self):
        self.mvars[M_TRAJ_VERSION] = 3.0
        # Number of points in a buffer
        self.mvars[M_TRAJ_BUFSIZE] = 1000
        # Address of A and B buffers
        #self.mvars[M_TRAJ_A_ADR] = 0x10020
        self.mvars[M_TRAJ_A_ADR] = 0x40000
        #self.mvars[M_TRAJ_B_ADR] = 0x12730
        self.mvars[M_TRAJ_B_ADR] = 0x30000

    def update(self):
        # print "Updating simulator"
        #write_to_file(filename, "\nUpdating simulator")
        for axis in range(1, 9):
            self.axes[axis].update()
        for csno in range(1, 16):
            #self.cs[csno].running_scan = True	# Elena add - may break stuff
            self.cs[csno].update()

#    def parse(self, message):
#        #write_to_file(filename, "\nEntering parse function")
#        try:
#            self.lastMessage = message
#            # split the message by whitespace
#            resp = ""
#            self.response = ""
#            self.lastResponse = ""
#            #write_to_file(filename, "\nMessage received: ")
#            #write_to_file(filename, repr(message))
#            for word in message.split():
#                word = word.upper()
#                #write_to_file(filename, "\nWord is: ")
#                #write_to_file(filename, repr(word))
#                logging.debug("Word: %s", word)
#                resp = ""
#                # Check for a starting hash
#                if '#' in word:
#                    #write_to_file(filename, "\n# in word")
#                    index = word.find('#')
#                    # Search for the number
#                    num = word[index:]
#                    self.caxis = int(filter(str.isdigit, num))
#                    logging.debug("Changing axis to %d", self.caxis)
#                if 'WL:$' in word:
#                    #write_to_file(filename, "\nWL:$ in word")
#                    logging.debug(word)
#                    self.parse_memory_write(word)
#                if '&' in word:
#                    #write_to_file(filename, "\n& in word")
#                    index = word.find('&')
#                    # Search for the number
#                    num = word[index:index+2]
#                    self.ccs = int(filter(str.isdigit, num))
#                    logging.debug("Changing CS to %d", self.ccs)
#                if '->' in word:
#                    #write_to_file(filename, "\n-> in word")
#                    if self.caxis == 1:
#                        resp = "A"
#                    elif self.caxis == 2:
#                        resp = "B"
#                    elif self.caxis == 3:
#                        resp = "C"
#                    elif self.caxis == 4:
#                        resp = "U"
#                    elif self.caxis == 5:
#                        resp = "V"
#                    elif self.caxis == 6:
#                        resp = "W"
#                    elif self.caxis == 7:
#                        resp = "X"
#                    elif self.caxis == 8:
#                        resp = "Y"
#                if 'B' in word and 'R' in word:
#                    #write_to_file(filename, "\nB and R in word")
#                    # Request to execute motion program
#                    index = word.find('B')
#                    # Search for the number
#                    num = word[index:]
#                    prog_no = int(filter(str.isdigit, num))
#                    self.cs[self.ccs].run_program()
#                    self.pvars[4001] = 1
#                    logging.debug("Execute motion program %d for CS %d", prog_no, self.ccs)
#                if 'J=' in word:
#                    #write_to_file(filename, "\nJ= in word")
#                    index = word.find('J=')
#                    # Search for the number
#                    num = word[index + 2:]
#                    # print "Pos demand: " + num
#                    logging.debug("Pos demand #%d (J=) %f", self.caxis, float(num))
#                    self.axes[self.caxis].move(float(num))
#                if '/' in word:
#                    #write_to_file(filename, "\n/ in word")
#                    self.axes[self.caxis].stop()
#                if "?" in word:
#                    #write_to_file(filename, "\n? in word")
#                    resp = self.parse_status_request(word)
#                if "%" in word:
#                    #write_to_file(filename, "\n% in word")
#                    resp = "100"
#                if 'LIST' in word:
#                    #write_to_file(filename, "\nLIST in word")
#                    return chr(0x07) + "\r"
#                if 'VER' in word:
#                    #write_to_file(filename, "\nVER in word")
#                    resp = "1.942"
#                elif 'V' in word:
#                    #write_to_file(filename, "\nV in word")
#                    resp = "0.0"
#                if 'F' in word:
#                    #write_to_file(filename, "\nF in word")
#                    resp = "0.0"
#                if 'Q' in word:
#                    #write_to_file(filename, "\nQ in word")
#                    resp = "0"
#                if 'M' in word:
#                    #write_to_file(filename, "\nM in word")
#                    index_m = word.find('M')
#                    mvar = None
#                    # Search for the number
#                    num = word[index_m:]
#                    index = word.find('=')
#                    writing = False
#                    if index > -1:
#                        value = num[index + 1:]
#                        num = num[:index + 1]
#                        writing = True
#                        mvar = int(filter(str.isdigit, num))
#                    else:
#                        i = index_m + 1
#                        mvar = ''
#                        #write_to_file(filename, ", string in which to find num is ")
#                        #write_to_file(filename, repr(num))
#                        #write_to_file(filename, ", word[index_m + 1] = ")
#                        #write_to_file(filename, word[i]) 
#                        #write_to_file(filename, ", appending to mvar")
#                        while (word[i]).isdigit(): #isnumeric() if was using Python3
#                            #write_to_file(filename, ".")
#                            mvar = mvar + word[i]
#                            i+=1
#                    #write_to_file(filename, ", num = ")
#                    #write_to_file(filename, num)
#                    #write_to_file(filename, ", mvar = ")
#                    #write_to_file(filename, mvar)
#                    if writing:
#                        #write_to_file(filename, ", now writing")
#                        logging.debug("Writing M[%d] = %s", mvar, value)
#                        self.mvars[mvar] = float(value)
#                    else:
#                        #write_to_file(filename, ", now setting resp by accessing m")
#                        #write_to_file(filename, mvar)
#                        #resp = str(self.mvars[int(filter(str.isdigit, num))]) #original line
#                        #resp = str(self.mvars[mvar])
#                        #write_to_file(filename, ", setting resp to ")
#                        #write_to_file(filename, repr(self.mvars[mvar]))
#                        resp = str(self.mvars[mvar])
#                        #write_to_file(filename, ", finished with 'M' block")
#                if 'CPU' in word:
#                    #write_to_file(filename, "\nCPU in word")
#                    resp = "DSP56321"
#                elif 'P' in word:
#                    #write_to_file(filename, "\nP in word")
#                    if '#' in word or word.strip() == 'P':
#                        resp = str(self.axes[self.caxis].readPosition())
#                    else:
#                        index = word.find('P')
#                        # Search for the number
#                        num = word[index:]
#                        index = word.find('=')
#                        writing = False
#                        if index > -1:
#                            value = num[index + 1:]
#                            num = num[:index + 1]
#                            writing = True
#                        pvar = int(filter(str.isdigit, num))
#                        if writing:
#                            logging.debug("Writing P[%d] = %s", pvar, value)
#                            self.pvars[pvar] = float(value)
#                        else:
#                            resp = str(self.pvars[int(filter(str.isdigit, num))])
#                        #resp = "0"
#                if 'CID' in word:
#                    #write_to_file(filename, "\nCID in word")
#                    resp = "603382"
#                elif 'I' in word:
#                    #write_to_file(filename, "\nI in word")
#                    index = word.find('I')
#                    # Search for the number
#                    num = word[index:]
#                    index = word.find('=')
#                    writing = False
#                    if index > -1:
#                        value = num[index + 1:]
#                        num = num[:index + 1]
#                        writing = True
#                    ivar = int(filter(str.isdigit, num))
#                    if ivar > 99 and ivar < 901:
#                        axno = int(ivar / 100)
#                        # print "Axis no: " + str(axno)
#                        varno = ivar - (100 * axno)
#                        # print "Var no: " + str(varno)
#                        if writing == True:
#                            self.axes[axno].writeIVar(varno, float(value))
#                            #print("\nI've commented out a line here")
#                        else:
#                            value = self.axes[axno].readIVar(varno)
#                            # print "Value: " + str(value)
#                            resp = str(value)
#                            #write_to_file(filename, "\nresp = str(value) = ")
#                            #write_to_file(filename, resp)
#                    else:
#                        if not writing:
#                            #resp = "0\r"
#                            resp = "$0\r"
#                            #write_to_file(filename, "\nresp = 0\\r")
#                #self.response += resp + "\r"
#                self.response += resp
#        except:
#            resp = ""
#        
#        #may cause problems down the line, but let's try it:
#        #write_to_file(filename,"\nself.response[-1:] = ")
#        #write_to_file(filename,repr(self.response[-1:]))
#        if self.response[-1:] != "\r":
#            self.response += "\r"
#        
#        #self.response = self.response[:-1]
#        #self.response += resp + "\r"
#        self.lastResponse = self.lastResponse + resp + " "
#
#        #write_to_file(filename, "\nin parse function, final output is: %r"%(self.response))
#        return self.response

    def parse(self, message):
    	# Define the lexer
    	# List of token names
	tokens = (
	    'END',
	    'ARROW',
	    'ENABLEPLC',
	    'WL',
	    'CID',
	    'LIST',
	    'IWRITE',
	    'IQUERY',
	    'HOME',
	    'MWRITE',
	    'MQUERY',
	    'CPU',
	    'PWRITE',
	    'PQUERYNUM',
	    'PQUERY',
	    'AXIS',
	    'JEQUAL',
	    'JADD',
	    'JSLASH',
	    'JPOS',
	    'JNEG',
	    '3QUESTION',
	    '2QUESTION',
	    '1QUESTION',
	    'AMPERSAND',
	    'PERCENT',
	    'VER',
	    'ABR',
	    'B',
	    'R',
	    'V',
	    'F',
	    'Q',
	    'K',
	    'NUMBER',
	    'LETTERSTRING',
	    'SYMBOL',
	)

	# Regex rules for simple tokens
	t_END = r'\r'

	# Regex rule for ->
	def t_ARROW(t):
	    r'\-\>'
	    global resp
	    #write_to_file(filename, '\n\'->\' detected, adding to resp')
	    if self.caxis == 1:
	        resp = resp + "A" +'\r'
	    elif self.caxis == 2:
	        resp = resp + "B" +'\r'
	    elif self.caxis == 3:
	        resp = resp + "C" +'\r'
	    elif self.caxis == 4:
	        resp = resp + "U" +'\r'
	    elif self.caxis == 5:
	        resp = resp + "V" +'\r'
	    elif self.caxis == 6:
	        resp = resp + "W" +'\r'
	    elif self.caxis == 7:
	        resp = resp + "X" +'\r'
	    elif self.caxis == 8:
	        resp = resp + "Y" +'\r'
	    #catch else?
	
	# Regex rule for ENABLE PLC
	def t_ENABLEPLC(t):
	    r'ENABLE\ PLC\d+'
	    self.enable_plc(int(t.value[10:]))
	    return t
	
	# Regex rule for WL:$
	def t_WL(t):
	    r'WL:$\d+'
	    self.parse_memory_write(t.value)
	    return t
	
	# Regex rule for CID
	def t_CID(t):
	    r'CID'
	    global resp
	    resp = resp + "603382" +'\r'
	    #write_to_file(filename, '\nresp = resp + \"603382\" +\'\\r\'')
	    return t

	# Regex for LIST
	def t_LIST(t):
	    r'LIST'
	    global resp
	    resp = resp + chr(0x07) + "\r"
	    #write_to_file(filename, '\nresp = resp + chr(0x07) + \'\\r\'')
	    return t

	# Regex rule for i number writing
	def t_IWRITE(t):
	    r'I\d+\=\d+|I\d+\=-\d+'
	    index = (t.value).find('=')
	    value = t.value[index + 1:]
	    num = t.value[1:index]
	    #write_to_file(filename, ('\ni string is ', str(t.value), ',i value is ', str(value),',i variable is number ',str(num)))
	    ivar = int(num)
	    self.mvars[ivar] = float(value)
	    if ivar > 99 and ivar < 901:
	        axno = int(ivar / 100)
	        varno = ivar - (100 * axno)
	        self.axes[axno].writeIVar(varno, float(value))
	        #write_to_file(filename, '\nsetting self.axes[{axno}].writeIVar({varno}, float({value}))')
	    #else:
	        #write_to_file(filename, '\nivar out of bounds for writing')
	    return t

	# Regex rule for i number querying
	def t_IQUERY(t):
	    r'I\d+'
	    ivar = int(t.value[1::])
	    global resp
	    if ivar > 99 and ivar < 901:
	        axno = int(ivar / 100)
	        varno = ivar - (100 * axno)
	        value = self.axes[axno].readIVar(varno)
	        resp = resp + str(value) +'\r'
	        #write_to_file(filename, ('\nresp = resp + ', str(value), ' + \'\\r\''))
	    else:
	        resp = resp + "$0\r"
	        #write_to_file(filename, '\nresp = resp + \"$0\\r\"')
	    return t

	# Regex rule for HM (HOME)
	def t_HOME(t):
	    #r'HM|HOME'
	    r'HM|HOME'
	    #write_to_file(filename, '\nHome')
	    self.axes[self.caxis].move(0.0)
	    return t
	
	# Regex rule for m number writing
	def t_MWRITE(t):
	    r'M\d+\=\d+|M\d+\=-\d+'
	    index = (t.value).find('=')
	    value = t.value[index + 1:]
	    num = t.value[1:index]
	    mvar = int(num)
	    self.mvars[mvar] = float(value)
	    #write_to_file(filename, ('\nm string is ', str(t.value), ',m value is ', str(value), ',m variable is number ', str(num), ', self.mvars[mvar] = float(value)'))
	    return t

	# Regex rule for m number querying
	def t_MQUERY(t):
	    r'M\d+'
	    mvar = int(t.value[1::])
	    global resp
	    resp = resp + str(self.mvars[mvar]) +'\r'
	    #write_to_file(filename, '\nresp = resp + self.mvars[mvar] +\'\\r\'')
	    return t

	# Regex for CPU
	def t_CPU(t):
	    r'CPU'
	    global resp
	    resp = resp + "DSP56321" +'\r'
	    #write_to_file(filename, '\nresp = resp + \"DSP56321\" +\'\\r\'')
	    return t

	# Regex rule for p number writing
	def t_PWRITE(t):
	    r'P\d+\=\d+|P\d+\=-\d+'
	    index = (t.value).find('=')
	    value = t.value[index + 1:]
	    num = t.value[1:index]
	    pvar = int(num)
	    self.pvars[pvar] = float(value)
	    #write_to_file(filename, ('\np string is ', str(t.value), ', p value is ', str(value), ', p variable is number ', str(num), ', self.pvars[pvar] = float(value)'))
	    return t

	# Regex for querying p number
	def t_PQUERYNUM(t):
	    r'P\d+'
	    num = int(t.value[1::])
	    global resp
	    resp = resp + str(self.pvars[int(num)]) +'\r'
	    #write_to_file(filename, '\nresp = resp + \'self.pvars[int(num)])\' +\'\\r\'')
	    return t

	# Regex for querying p number
	def t_PQUERY(t):
	    r'P'
	    global resp
	    resp = resp + str(self.axes[self.caxis].readPosition()) +'\r'
	    #write_to_file(filename, '\nresp = resp + str(self.axes[self.caxis].readPosition()) +\'\\r\'')
	    return t

	# Regex rule for # numbers which is telling which axis to address
	def t_AXIS(t):
	    r'\#\d+'
	    self.caxis = int(t.value[1::])
	    #write_to_file(filename, ('\nChanging axis to ', str(self.caxis)))
	    return t

	# Regex for J= terms aka pos demand
	def t_JEQUAL(t):
	    r'J\=\d+|J\=-\d+'
	    num = float(t.value[2::])
	    #write_to_file(filename, ('\nPos demand: ', str(num)))
	    self.axes[self.caxis].move(num)
	    return t
	
	# Regex for J^ positive terms (jog by a set amount from current position)
	def t_JADD(t):
	    r'J\^\d+|J\^-\d+'
	    num = float(t.value[2::])
	    #write_to_file(filename, ('\nPos demand from current: ', str(num)))
	    self.axes[self.caxis].move(self.axes[self.caxis].position + num)
	    return t

	# Regex rule for /
	def t_JSLASH(t):
	    r'J\/'
	    self.axes[self.caxis].stop()
	    #write_to_file(filename, ('\nStopping axis ', str(self.caxis)))
	    return t

	# Regex rule for J+
	def t_JPOS(t):
	    r'J\+'
	    #request to move to upper movement limit
	    self.axes[self.caxis].move(self.axes[self.caxis].ivars[13])
	    #write_to_file(filename, '\nJog in positive direction')
	    return t

	# Regex rule for J+
	def t_JNEG(t):
	    r'J\-'
	    #request to move to lower movement limit
	    self.axes[self.caxis].move(self.axes[self.caxis].ivars[14])
	    #write_to_file(filename, '\nJog in negative direction')
	    return t

	# Regex rule for ???
	def t_3QUESTION(t):
	    r'\?\?\?'
	    global resp
	    resp = resp + '000000000000' +'\r'
	    #write_to_file(filename, '\nresp = resp + \'000000000000\' +\'\\r\'')
	    return t

	# Regex rule for ??
	def t_2QUESTION(t):
	    r'\?\?'
	    global resp
	    resp = resp + self.cs[self.ccs].get_status() +'\r'
	    #write_to_file(filename, '\nresp = resp + self.cs[self.ccs].get_status() +\'\\r\'')
	    return t

	# Regex rule for ?
	def t_1QUESTION(t):
	    r'\?'
	    global resp
	    resp = resp + self.axes[self.caxis].getStatus() +'\r'
	    #write_to_file(filename, '\nresp = resp + self.axes[self.caxis].getStatus() +\'\\r\'')
	    return t

	# Regex rule for & (which changes CS)
	def t_AMPERSAND(t):
	    r'\&\d+'
	    self.ccs = int(t.value[1::])
	    #write_to_file(filename, ('\nChanging CS to ', str(self.ccs)))
	    return t

	# Regex rule for %
	def t_PERCENT(t):
	    r'%'
	    global resp
	    resp = resp + '100' +'\r'
	    #write_to_file(filename, '\nresp = resp + \'100\' +\'\\r\'')
	    return t

	# Regex for VER
	def t_VER(t):
	    r'VER'
	    global resp
	    resp = resp + '1.942' +'\r'
	    #write_to_file(filename, "\nresp = resp + '1.942' +\'\\r\'")
	    return t

	# Abort currently running motion program and start another
	def t_ABR(t):
	    r'ABR\d+.\d+|ABR\d+'
	    prog_no = int(t.value[3::])
	    self.cs[self.ccs].motion_prog = prog_no
	    #self.cs[self.ccs].run_program()	# Diamond motion program
	    self.pvars[4001] = 1	# not sure what this does or why
	    #write_to_file(filename,("\nAborting current motion program and starting to execute motion program ", str(prog_no), ' for CS ', str(self.css),", self.pvars[4001] = 1"))
	    return t
	
	# Point the addressed coordinate system to a motion program
	def t_B(t):
	    r'B\d+.\d+|B\d+'
	    prog_no = int(t.value[1::])
	    self.cs[self.ccs].motion_prog = prog_no
	    self.pvars[4001] = 1	# not sure what this does or why
	    #write_to_file(filename,("\nPointing to motion program ", str(prog_no), ' for CS ', str(self.css),", self.pvars[4001] = 1"))
	    return t
	
	# Run motion program
	def t_R(t):
	    r'R'
	    prog_no = self.cs[self.ccs].motion_prog
	    #self.cs[self.ccs].run_program()	# Diamond motion program
	    self.pvars[4001] = 1	# not sure what this does or why
	    #write_to_file(filename,("\nRun motion program ", str(prog_no), ' for CS ', str(self.css),", self.pvars[4001] = 1"))
	    return t

	# Regex for V
	def t_V(t):
	    r'V'
	    global resp
	    velocity = self.axes[self.caxis].readIVar(22)
	    resp = resp + str(velocity) +'\r'
	    #write_to_file(filename, ("\nresp = resp + self.ivars[22] (= ", velocity,") +\'\\r\'"))
	    return t

	# Regex for F
	def t_F(t):
	    r'F'
	    global resp
	    following_error = self.axes[self.caxis].dmd_position - self.axes[self.caxis].position
	    resp = resp + str(following_error) +'\r'
	    #write_to_file(filename, ("\nresp = resp + following error (=",following_error,") +\'\\r\'"))
	    return t

	# Regex for Q
	def t_Q(t):
	    r'Q'
	    global resp
	    resp = resp + '0' +'\r'
	    #write_to_file(filename, "\nresp = resp + '0' +\'\\r\'")
	    return t

	# Regex for K (Kill)
	def t_K(t):
	    r'K'
	    self.axes[self.caxis].stop()
	    self.axes[self.caxis].amp_enabled = 0
	    #write_to_file(filename, ('\nKilling axis ', str(self.caxis)))
	    return t

	# General catch-all regex rules, should go after main specific rules:

	# Regex rule for numbers
	def t_NUMBER(t):
	    r'\d+'
	    t.value = int(t.value)
	    #write_to_file(filename, ("\nCaught following number from input that couldn't be processed with current code: ", str(t.value)))
	    return t

	# Regex rule for letters
	def t_LETTERSTRING(t):
	    r'[a-zA-Z]+'
	    #write_to_file(filename, ("\nCaught following letter(s) from input that couldn't be processed with current code: ", str(t.value)))
	    return t

	# Regex rule for symbols (for now, everything not a letter or number)
	def t_SYMBOL(t):
	    r'[^0-9|^a-zA-Z]'
	    #write_to_file(filename, ("\nCaught following symbol from input that couldn't be processed with current code: ", str(t.value)))
	    return t

	# A string containing ignored characters (spaces and tabs)
	t_ignore = ' \t'

	# Error handling rule
	def t_error(t):
	    #write_to_file(filename, ("\nError: Illegal character: ", repr(t.value[0])))
	    t.lexer.skip(1)


	# Build the lexer
	lexer = lex.lex()

	# Use the lexer

	# String to input
	input_string = message.upper()

	# initialise stuff
	global resp
	resp = ""
	self.response = ""
        self.lastResponse = ""
        #write_to_file(filename, ("\nMessage received: ", repr(message)))

	# Give lexer the input
	lexer.input(input_string)

	# Tokenize
	while True:
	    tok = lexer.token()
	    if not tok:
	        break   # No more input
	    #write_to_file(filename, ("\n",str(tok)))

	self.response = resp #should probs replace resp with self.response everywhere
	if self.response[-1:] != "\r": #may no longer be necessary
	    self.response += "\r"
	
        self.lastResponse = self.lastResponse + resp + " "

        #write_to_file(filename, "\nin parse function, final output is: %r"%(self.response))
        return self.response


    def set_m_var(self, index, value):
        self.mvars[index] = value

    def get_m_var(self, index):
        return self.mvars[index]

    def set_p_var(self, index, value):
        self.pvars[index] = value

    def get_p_var(self, index):
        return self.pvars[index]

    def read_memory_address(self, address):
        return self.memory[address]

    def read_position(self, address):
        return self.convertToDouble(self.memory[address])

    def enable_plc(self, plc_num):
    	try:
    	    f = open(self.plc_file, 'r')
    	    #write_to_file(filename, '\nOpening %r'%(self.plc_file))
	except:
    	    logging.debug('Could not open chosen PLC file, reverting to default file')
    	    #write_to_file('\nCould not open chosen PLC file, reverting to default file')
    	    f = open('defaultPLCs.py', 'r')
	finally:
    	    exec(f.read())
    	    f.close()
    
    def parse_memory_write(self, word):
        address = 0
        # Split by commas
        for data in word.split(','):
            logging.debug("Data item: %s", data)
            if 'WL:$' in data:
                # This is the address item so parse it
                index = data.find('WL:$')
                # Search for the number
                num = data[index + 4:]
                address = int(num, 16)
                logging.debug("Address to write to: %d", address)
            else:
                # This will be a write, so place the number in memory
                index = data.find('$')
                # Search for the number
                num = data[index + 1:]
                self.memory[address] = int(num, 16)
                logging.debug("Value to write: %d", self.memory[address])
                address += 1

#    def parse_status_request(self, word):
#        if word == "???":
#            resp = "000000000000"
#        else:
#            if '??' in word:
#                resp = self.cs[self.ccs].get_status()
#            else:
#                if '?' in word:
#                    resp = self.axes[self.caxis].getStatus()
#        return resp

    def is_number(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def getRunning(self):
        return self.running

    def setRunning(self, running):
        self.running = running

    def convertToDouble(self, value):
        logging.debug("Converting value: %x", value)
        exponent = value & 0xFFF
        exponent = exponent - 0x800
        mantissa = value >> 12
        if mantissa & 0x800000000:
            negative = -1.0
            mantissa = 0xFFFFFFFFF - mantissa
        else:
            negative = 1.0

        for index in range(0, exponent):
            mantissa = mantissa / 2.0

        while mantissa > 1.0:
            mantissa = mantissa / 2.0
        mantissa = mantissa * 2.0
        if exponent >= 0:
            for index in range(0, exponent):
                mantissa = mantissa * 2.0
        else:
            for index in range(0, (exponent*-1)):
                mantissa = mantissa / 2.0

        mantissa *= negative
        logging.debug("Converted value: %f", mantissa)
        return mantissa


if __name__ == "__main__":
    # logging.basicConfig(filename="simulator.log", filemode='w',
    #                     level=logging.DEBUG)
    logging.basicConfig(filename="/tmp/pmac-simulator.log", filemode='w',
                        level=logging.ERROR)

    # a single command line parameter provides the port and runs with no UI
    # no parameter means run interactively
    if len(sys.argv) == 2:
        app = SimulatedPmacAppNoGui(sys.argv[1])
    elif len(sys.argv) == 3:
    	app = SimulatedPmacAppNoGui(sys.argv[1], sys.argv[2])
    else:
        app = SimulatedPmacAppGui()

    app.run()
