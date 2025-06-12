import time
import os
import sys
import select
import termios
import tty

# Configuração inicial do terminal (Unix)
if sys.platform != 'win32':
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

# Representação dos dígitos em 7 segmentos (3 linhas)
DIGITS = {
    0: [' _ ', '| |', '|_|'],
    1: ['   ', '  |', '  |'],
    2: [' _ ', ' _|', '|_ '],
    3: [' _ ', ' _|', ' _|'],
    4: ['   ', '|_|', '  |'],
    5: [' _ ', '|_ ', ' _|'],
    6: [' _ ', '|_ ', '|_|'],
    7: [' _ ', '  |', '  |'],
    8: [' _ ', '|_|', '|_|'],
    9: [' _ ', '|_|', ' _|'],
    ':': ['   ', ' • ', ' • '],
    ' ': ['   ', '   ', '   ']
}


class DigitalClock:
    def __init__(self):
        self.hours = 12
        self.minutes = 0
        self.seconds = 0
        self.alarm_hours = 6
        self.alarm_minutes = 30
        self.alarm_active = False
        self.alarm_triggered = False
        self.setting_mode = None  # None, 'time', 'alarm'
        self.setting_step = 0  # 0=hours, 1=minutes
        self.last_blink = 0
        self.blink_state = True
        self.last_second = time.time()

    def increment_time(self, unit):
        if unit == 'hours':
            self.hours = (self.hours + 1) % 24
        elif unit == 'minutes':
            self.minutes = (self.minutes + 1) % 60
        elif unit == 'seconds':
            self.seconds = (self.seconds + 1) % 60

    def increment_alarm(self, unit):
        if unit == 'hours':
            self.alarm_hours = (self.alarm_hours + 1) % 24
        elif unit == 'minutes':
            self.alarm_minutes = (self.alarm_minutes + 1) % 60

    def check_alarm(self):
        if (self.alarm_active and
                not self.alarm_triggered and
                self.hours == self.alarm_hours and
                self.minutes == self.alarm_minutes and
                self.seconds == 0):
            self.alarm_triggered = True
            return True
        return False

    def reset_alarm_trigger(self):
        if self.minutes != self.alarm_minutes:
            self.alarm_triggered = False

    def update_clock(self):
        current_time = time.time()
        if current_time - self.last_second >= 1:
            self.seconds = (self.seconds + 1) % 60
            if self.seconds == 0:
                self.minutes = (self.minutes + 1) % 60
                self.reset_alarm_trigger()
                if self.minutes == 0:
                    self.hours = (self.hours + 1) % 24
            self.last_second = current_time

    def render_digit(self, digit):
        return DIGITS.get(digit, DIGITS[' '])

    def format_time(self, hours, minutes, seconds, show_seconds=True):
        digits = []
        # Horas
        digits.append(hours // 10)
        digits.append(hours % 10)
        digits.append(':')
        # Minutos
        digits.append(minutes // 10)
        digits.append(minutes % 10)

        if show_seconds:
            digits.append(':')
            # Segundos
            digits.append(seconds // 10)
            digits.append(seconds % 10)

        return digits

    def display(self, digits):
        lines = ['', '', '']
        for digit in digits:
            segments = self.render_digit(digit)
            for i in range(3):
                lines[i] += segments[i]
        return '\n'.join(lines)

    def blink_effect(self, digits, current_time):
        if current_time - self.last_blink > 0.5:
            self.blink_state = not self.blink_state
            self.last_blink = current_time

        if not self.blink_state:
            if self.setting_step == 0:  # Piscar horas
                digits[0] = ' '
                digits[1] = ' '
            elif self.setting_step == 1:  # Piscar minutos
                digits[3] = ' '
                digits[4] = ' '
        return digits

    def get_display_output(self):
        current_time = time.time()
        show_seconds = self.setting_mode != 'alarm'

        # Selecionar o que mostrar
        if self.setting_mode == 'alarm':
            digits = self.format_time(
                self.alarm_hours,
                self.alarm_minutes,
                0,
                show_seconds
            )
            digits = self.blink_effect(digits, current_time)
        else:
            digits = self.format_time(
                self.hours,
                self.minutes,
                self.seconds,
                show_seconds
            )

        return self.display(digits)

    def handle_input(self, key):
        # Trocar entre modos
        if key == 'a':
            self.setting_mode = 'alarm' if self.setting_mode != 'alarm' else None
            self.setting_step = 0
            return

        if key == 't':
            self.setting_mode = 'time' if self.setting_mode != 'time' else None
            self.setting_step = 0
            return

        # Ativar/desativar alarme
        if key == ' ':
            self.alarm_active = not self.alarm_active
            return

        # Processar ajustes
        if self.setting_mode == 'time':
            if key == 'h' and self.setting_step == 0:
                self.increment_time('hours')
            elif key == 'm' and self.setting_step == 1:
                self.increment_time('minutes')
            elif key == 's':
                self.seconds = 0
            elif key == '\n':  # Enter
                self.setting_step = (self.setting_step + 1) % 2

        elif self.setting_mode == 'alarm':
            if key == 'h' and self.setting_step == 0:
                self.increment_alarm('hours')
            elif key == 'm' and self.setting_step == 1:
                self.increment_alarm('minutes')
            elif key == '\n':  # Enter
                self.setting_step = (self.setting_step + 1) % 2


def get_key():
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getch().decode()
    else:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
    return None


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    clock = DigitalClock()

    try:
        while True:
            clear_screen()

            # Atualizar e mostrar relógio
            clock.update_clock()
            print("Relógio Digital (7 Segmentos)")
            print(clock.get_display_output())

            # Verificar alarme
            if clock.check_alarm():
                print("\nALARME ATIVADO!")
                print('\a')  # Beep do sistema

            # Mostrar status
            print(f"\nAlarme: {'ON' if clock.alarm_active else 'OFF'} "
                  f"| {clock.alarm_hours:02d}:{clock.alarm_minutes:02d}")

            if clock.setting_mode == 'time':
                print("\nModo Ajuste de Hora")
                steps = ['HORA', 'MINUTOS']
                print(f"Passo atual: {steps[clock.setting_step]}")
                print("h: +Hora | m: +Minuto | s: Zerar segundos | Enter: Próximo")

            elif clock.setting_mode == 'alarm':
                print("\nModo Ajuste de Alarme")
                steps = ['HORA', 'MINUTOS']
                print(f"Passo atual: {steps[clock.setting_step]}")
                print("h: +Hora | m: +Minuto | Enter: Próximo")

            print("\nControles:")
            print("a: Ajustar alarme | t: Ajustar tempo | Espaço: Liga/Desliga alarme | q: Sair")

            # Processar entrada
            key = get_key()
            if key == 'q':
                break
            if key:
                clock.handle_input(key)

            time.sleep(0.1)

    finally:
        # Restaurar configurações do terminal (Unix)
        if sys.platform != 'win32':
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    main()