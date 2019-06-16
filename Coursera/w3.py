
class Planet:

    count = 0

    def __init__(self, name):
        self.name = name
        Planet.count += 1

    def __repr__(self):
        return f"Planet {self.name}"

    def __str__(self):
        return f"Planet {self.name}"


class Robot:

    def __init__(self, power):

        if power < 0:
            self.power = 0
        else:
            self.power = power


class NewRobot:

    def __init__(self, power):
        self._power = power

    power = property()

    @power.setter
    def power(self, value):
        if value < 0:
            self._power = 0
        else:
            self._power = value

    @power.getter
    def power(self):
        return self._power

    @power.deleter
    def power(self):
        print("No more power for this Robot")
        del self._power


# https://www.python-course.eu/python3_class_and_instance_attributes.php


class RobotA:

    __counter = 0

    def __init__(self, name, build_year):
        # Protected attribute, only available via getter/setter methods. obj.__name won't work
        self.__name = name
        self.__build_year = build_year
        type(self).__counter += 1
        print(f"{RobotA.__counter} robots created")

    def get_name(self):
        return self.__name

    def get_build_year(self):
        return self.__build_year

    def rename(self, name):
        self.__name = name

    def rebuild(self, build_year):
        self.__build_year = build_year

    def __str__(self):
        return f"[str] Robot {self.get_name()}, built in {self.get_build_year()}"

    def __repr__(self):
        return f"[repr] Robot {self.get_name()}, built in {self.get_build_year()}"

    @classmethod
    def total_robots(cls):
        return cls.__counter
