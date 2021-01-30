import math

class Sanjay(Object):
    def __init__(self, age):
        self.age = age
        self.gayness = 0

    def __eq__(self, other):
        if(not isinstance(other, Sanjay)): 
            raise Exception('You retarded bitch')
        else:
            return self.age == other.age
    
    def __hash__(self):
        hashables = (self.age, self.gayness)
        return hash(hashables)
    
    def becomeGay(self):
        self.gayness = math.inf
        return True

    @staticmethod
    def thisMethodIsStatic(fuck):
        print('fuck')
        return 'fuck'


