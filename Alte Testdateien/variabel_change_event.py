class GlobalWealth(object):
    def __init__(self):
        self._global_wealth = 10.0
        self._observers = []

    @property
    def global_wealth(self):
        return self._global_wealth

    @global_wealth.setter
    def global_wealth(self, value):
        self._global_wealth = value
        for callback in self._observers:
            print('announcing change')
            callback(self._global_wealth)

    def bind_to(self, callback):
        print('bound')
        self._observers.append(callback)


class Person(object):
    def __init__(self, data):
        self.wealth = 1.0
        self.data = data
        self.data.bind_to(self.update_how_happy)
        self.happiness = self.wealth / self.data.global_wealth

    def update_how_happy(self, global_wealth):
        self.happiness = self.wealth / global_wealth


		
class A(object):

    def m(self, p_value):
         print(p_value)

    @property
    def p(self):
        return self._p 

    @p.setter
    def p(self, value):
        self._p = value
        self.m(value
		
if __name__ == '__main__':
    data = GlobalWealth()
    p = Person(data)
    print(p.happiness)
    data.global_wealth = 1.0
    print(p.happiness)

# https://stackoverflow.com/questions/12998926/clean-way-to-disable-setattr-until-after-initialization
# https://stackoverflow.com/questions/6190468/how-to-trigger-function-on-value-change