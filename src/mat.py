import math


class Vector:
    def __init__(self,cordinates):
        self.cordinates = cordinates 

    @staticmethod
    def create_vector(v):
        if v.count("{") != 1:
            raise ValueError("antal af '{' er forkert")
        if v.count("}") != 1:
                    raise ValueError("antal af '}' er forkert")

        v = v.replace("{","").replace("}","")
        v = v.split(",")
        v = [x.strip() for x in v]
        return Vector(v)

    def __str__(self):
          v = ", ".join(self.cordinates)
          return "{" + v + "}"

    def __add__(self, other):
        result = []
        for x,y in zip(self.cordinates,other.cordinates):
            result.append(str(float(x) + float(y)))
        return Vector(result)

    def __sub__(self, other):
        result = []
        for x,y in zip(self.cordinates,other.cordinates):
            result.append(str(float(x) - float(y)))
        return Vector(result)        

    def __abs__(self):
        result = 0
        for x in self.cordinates:
              result += float(x)**2
    
        return math.sqrt(result) 


    def __len__(self):
         return len(self.cordinates)

    @staticmethod
    def dot_product(a,b):
        v = 0

        for x,y in zip(a.cordinates, b.cordinates):
            v+=(float(x)*float(y))
        
        return v
    @staticmethod
    def cross_product(a, b):
        if len(a) != 3 and len(b) != 3:
            raise ValueError("du kan kun lave kryds product med 3d vektorer")
        a = [float(x) for x in a.cordinates]
        b = [float(x) for x in b.cordinates]
        return [a[1]*b[2] - a[2]*b[1],
                a[2]*b[0] - a[0]*b[2],
                a[0]*b[1] - a[1]*b[0]]
