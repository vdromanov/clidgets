#/us/bin/env python
import curses
from curses import wrapper

class ProtectedInputLine(object): #A window, containing input field & left side text label

    def __init__(self, parent_window, initial_y, initial_x, height=None, width=None, title=None, label=None):
        curses.curs_set(0)

        self.initial_y = initial_y
        self.initial_x = initial_x
        self.height = 10 if not height else height
        self.width = 20 if not width else width
        self.title = title
        self.label = label #Information on the left of input field

        #Configurable params. TODO: add config parser
        self.info_width = 0 #Max length of text strings on the side of input field
        self.info_height = 0 #Height of text on the side of window (number of rows)
        self.input_field_length = 10
        self.allowed_chars = '0123456789'
        self.vertical_offset_before_label = 1 #Between title and label&input field
        self.hor_offset_before_input_field = 1 #Between label text & input field
        self.enter_chars = ('KEY_ENTER', '\n')
        self.backspace_chars = ('KEY_BACKSPACE', '\b', '\x7f')

        self.channel_window = parent_window.derwin(self.height, self.width, self.initial_y, self.initial_x)

    def set_title(self):
        self.channel_window.addstr(0, 0, self.title, curses.A_BOLD)
        self.vertical_offset_before_label += 1

    def set_text_info(self, contents_string, y=None, x=0):
        offsets_list = [] #A list, containing lengths of title strings

        if not y: #Possible to force set x & y
            y = self.vertical_offset_before_label

        for line in contents_string.strip().split('\n'):
            self.channel_window.addstr(y, x, line if line else contents_string)
            y += 1
            offsets_list.append(len(line))

        if len(offsets_list):
            self.info_width = max(offsets_list) #Horizontal offset before input field
            self.info_height = y - self.vertical_offset_before_label

    def make_input_field(self, y=None, x=None):
        if not y:
            y = self.vertical_offset_before_label

        if not x:
            x = self.info_width + self.hor_offset_before_input_field

        self.channel_window.addstr(y, x, ' ' * self.input_field_length, curses.A_REVERSE)
        self.input_field_position = [y, x]

    def check_input_char_correctness(self, char):
        return True if char in self.allowed_chars else False

    def get_correct_input_from_field(self): #Checks input correctness by char & prints correct chars in input field
        chars_list = []
        length_counter = 0

        while length_counter <= self.input_field_length:
            ascii_char = self.channel_window.getkey(self.input_field_position[0], self.input_field_position[1]) #Unicode number

            if ascii_char in self.enter_chars:
                break #Stop interacting with input field

            #Delete chars from screen & values from memory
            elif ascii_char in self.backspace_chars and length_counter > 0: #Check we aren't deleting title symbols
                self.channel_window.delch(self.input_field_position[0], self.input_field_position[1] - 1)
                self.channel_window.refresh()
                self.input_field_position[1] -= 1
                try:
                    chars_list.pop() #Deleting values from memory
                    length_counter -= 1
                except IndexError:
                    pass

            if self.check_input_char_correctness(ascii_char):
                self.channel_window.addch(ascii_char, curses.A_REVERSE)
                chars_list.append(ascii_char)
                self.channel_window.refresh()
                self.input_field_position[1] += 1 #Char position counter
                length_counter += 1
            else:
                curses.beep()

        return ''.join(chars_list)

    def get_window_object_to_force_interact_with(self):
        return self.channel_window

    def get_real_dimensions(self):
        real_height = self.info_height + self.vertical_offset_before_label
        real_width = self.info_width + self.hor_offset_before_input_field + self.input_field_length

        return (real_height, real_width)

    def show_window_contents(self):
        if self.title:
            self.set_title()

        self.set_text_info(self.label)
        self.make_input_field()
        real_dimensions = self.get_real_dimensions()
        self.channel_window.resize(real_dimensions[0], real_dimensions[1])
        self.channel_window.refresh()


class DialogWindow(object): #A floating window

    def __init__(self, window_under, y, x, contents, height=None, width=None):
        curses.curs_set(0)

        #Window position & dimensions
        self.y = y
        self.x = x
        self.height = 20 if not height else height
        self.width = 60 if not width else width
        self.width_coeff = 0.9
        self.height_coeff = 0.85
        self.side_margins_coeff = 0.2 #Space from beginning of line in yes/no
        self.vertical_label_offset = 1

        self.contents = contents #A string to show above the dialogue
        self.window_under = window_under
        self.state = None

        #Terminal settings
        self.up_chars = ('KEY_UP', 'j')
        self.down_chars = ('KEY_DOWN', 'k')
        self.enter_keys = ('KEY_ENTER', '\n')
        self.yes_keys = ('y', 'KEY_RIGHT')
        self.no_keys = ('n', 'KEY_LEFT')
        self.yes_string = '<YES>'
        self.no_string = '<NO>'

        self.parse_contents()

        self.show()

    def set_text_field_dimensions(self):
        self.tex_field_width = int(self.width * self.width_coeff)
        self.tex_field_height = int(self.height * self.height_coeff)

    def parse_contents(self): #Add \n's to fit the width of text field
        self.set_text_field_dimensions()
        final_list_of_strings = []
        one_row = ''
        values = self.contents.strip().split()

        for i, string in enumerate(values):
            if len(one_row) < self.tex_field_width:
                one_row += (string + ' ')
            else:
                row = one_row.replace(values[i-1], '').center(self.width, '*')
                final_list_of_strings.append(row + '\n')
                one_row = '' + values[i-1] + ' '
                
        self.parsed_content = tuple(final_list_of_strings) #Each element is a string row

    def draw_text_field_from_list(self, strings_list):
        y = self.vertical_label_offset

        for line in strings_list:
            self.working_window.addstr(y, 1, line)
            y += 1

        self.working_window.box()
        self.working_window.refresh()

    def make_scrollable_text_field(self):
        upper_limit = 0
        lower_limit = self.tex_field_height - 1

        if len(self.parsed_content) > self.tex_field_height:

            while lower_limit <= len(self.parsed_content): #While between 0 and last element
                visible_strings = self.parsed_content[upper_limit:lower_limit]
                self.draw_text_field_from_list(visible_strings)

                #Moving a slice of defined range (self.max_height) in a list of strings
                interact_char = self.working_window.getkey()
                if interact_char in self.up_chars:
                    if upper_limit >= 0:
                        upper_limit -= 1
                        lower_limit -= 1
                    else:
                        curses.beep()
                elif interact_char in self.down_chars:
                    upper_limit += 1
                    lower_limit += 1

        else:
            self.draw_text_field_from_list(self.parsed_content)

    def allign_string(self, contents):
        return contents.center(int((self.tex_field_width) / 2), ' ')

    def make_yesno_window(self):
        self.yesno_win = self.working_window.derwin(1, self.width - 2, self.tex_field_height + 1, 1)
        self.yesno_win.addstr(0, 0, self.allign_string(self.yes_string) + self.allign_string(self.no_string))
        self.yesno_win.refresh()

    def indicate_state(self, state):
        self.yesno_win.erase()
        if state == 'YES':
            self.yesno_win.addstr(0, 0, self.allign_string(self.yes_string), curses.A_BOLD)
            self.yesno_win.addstr(0, self.width / 2, self.allign_string(self.no_string))
        elif state == 'NO':
            self.yesno_win.addstr(0, self.width / 2, self.allign_string(self.no_string), curses.A_BOLD)
            self.yesno_win.addstr(0, 0, self.allign_string(self.yes_string))
        self.yesno_win.refresh()

    def get_input_from_yeson(self):
        answer = None
        self.indicate_state('NO')

        while 1:
            input_char = self.yesno_win.getkey()
            if input_char in self.yes_keys:
                self.indicate_state('YES')
                answer = True
            elif input_char in self.no_keys:
                self.indicate_state('NO')
                answer = False
            elif answer != None and input_char in self.enter_keys:
                break
            else:
                curses.beep()

        self.state = answer

    def show(self):
        self.working_window = curses.newwin(self.height, self.width, self.y, self.x)
        self.make_yesno_window()
        self.make_scrollable_text_field()
        state = self.get_input_from_yeson()
        self.working_window.touchwin()

    def hide(self):
        del self.working_window
        self.window_under.touchwin()
        self.window_under.refresh()

    def get_state(self):
        return self.state



if __name__ == '__main__':

    def test_input_string(stdscr):
        initial_y = 5
        initial_x = 5

        stdscr.clear()

        channel_1_phi = ProtectedInputLine(stdscr, initial_y, initial_x, 10, 20, 'Ch:1 PH:L1', 'Phi')
        channel_1_phi.show_window_contents()

        dimensions = channel_1_phi.get_real_dimensions()

        channel_1_gain = ProtectedInputLine(stdscr, initial_y + dimensions[0], initial_x, 10, 20, label='Gain')
        channel_1_gain.show_window_contents()

        stdscr.getch()

        phi_string = channel_1_phi.get_correct_input_from_field()
        gain_string = channel_1_gain.get_correct_input_from_field()

        stdscr.addstr(20, 20, phi_string)
        stdscr.addstr(21, 20, gain_string)
        stdscr.refresh()
        stdscr.getch()

    def test_yesno_window(stdscr):
        initial_x = 35
        initial_y = 10
        contents_string = '2132132132 11321321 312312312 fdfds\nfsdf sdfdsfsdfsdfsdf rewrwew\nrewrwerew ffdsdfdfsdfds dfd' * 25

        stdscr.clear()
        stdscr.addstr('vvrewgrewggwContents\ntwretwertwe\nrrtretw')
        stdscr.refresh()
        stdscr.getch()

        window = DialogWindow(stdscr, initial_y, initial_x, contents=contents_string)
        state = window.get_state()
        stdscr.refresh()
        stdscr.getch()
        window.hide()
        if state:
            stdscr.addstr(8, 9, 'Returned true')
        stdscr.getch()

    
    wrapper(test_yesno_window)
