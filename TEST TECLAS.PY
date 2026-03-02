import keyboard

keyboard.hook(lambda e: print(e.name, e.scan_code))
keyboard.wait()