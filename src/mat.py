import math
from matplotlib.figure import Figure
import numpy as np


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
        if len(self) != len(other):
            raise ValueError("vektorerne skal have samme længde")
        result = []
        for x,y in zip(self.cordinates,other.cordinates):
            result.append(str(float(x) + float(y)))
        return Vector(result)

    def __sub__(self, other):
        if len(self) != len(other):
            raise ValueError("vektorerne skal have samme længde")
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

    def __getitem__(self, key):
        return self.cordinates[key]

    def __setitem__(self, key, value):
        try: value = float(value)
        except: raise ValueError("alle index i en vektor skal være tal")
        self.cordinates[key] = str(value)

    @staticmethod
    def dot_product(a,b):
        v = 0

        for x,y in zip(a.cordinates, b.cordinates):
            v+=(float(x)*float(y))
        
        return v
    @staticmethod
    def cross_product(a, b):
        if len(a) != 3 or len(b) != 3:
            raise ValueError("du kan kun lave kryds product med 3d vektorer")
        a = [float(x) for x in a.cordinates]
        b = [float(x) for x in b.cordinates]
        return Vector([str(a[1]*b[2] - a[2]*b[1]),
            str(a[2]*b[0] - a[0]*b[2]),
            str(a[0]*b[1] - a[1]*b[0])])
    
    @staticmethod
    def scalar_product(k,a):
        result = []
        for part in a.cordinates:
            result.append(str(float(part)*float(k)))

        return Vector(result)

    @staticmethod
    def det(*args):
        for part in args:
            if len(part) != len(args):
                raise ValueError("Der skal være lige så mange vektorer som længden af vektorerne")
        flip = []
        i =0
        while i < len(args):
            temp = []
            for part in args:
                temp.append(float(part[i]))
            flip.append(temp)
            i += 1

        M = np.array(flip)
        return np.linalg.det(M)
            
    @staticmethod
    def enhedsvektor(a):
        if abs(a) == 0:
            raise ValueError("nulvektoren har ingen enhedsvektor")
        k = 1/abs(a)

        return Vector.scalar_product(k,a)

    @staticmethod
    def vinkel_mellem_vektorer(a,b):
        top = Vector.dot_product(a,b)
        bottom = abs(a)*abs(b)
        if bottom == 0:
            raise ValueError("du kan ikke finde vinklen med en nulvektor")
        return math.acos(max(-1, min(1, top/bottom)))

    @staticmethod
    def tværvektor(a):
        if len(a) != 2:
            raise ValueError("du kan kun finde en tvær vektor for 2d vektorer")
        return  Vector([str(0-float(a[1])),str(float(a[0]))])
        

    @staticmethod

    def projektion(a,b):
        top = Vector.dot_product(a,b)
        bottom = abs(b)**2
        if bottom == 0:
            raise ValueError("du kan ikke projicere på en nulvektor")

        return Vector.scalar_product(top/bottom,b)



    @staticmethod
    def plot(*vectors):
        dims = {len(v) for v in vectors}
        if dims != {2} and dims != {3}:
            raise ValueError("du kan kun plotte 2D eller 3D vektorer, og de skal have samme dimension")
        three_d = dims == {3}
        colors = ["#00d9ff", "#ff6ec7", "#ffd166", "#06ffa5", "#c77dff", "#ff9e6d"]
        coords = [[float(x) for x in v.cordinates] for v in vectors]
        lim = max(abs(x) for c in coords for x in c)*1.2 or 1
        fig = Figure(figsize=(5, 4),layout="constrained")
        fig.patch.set_facecolor("#404040")
        if three_d:
            ax = fig.add_subplot(projection="3d")
            ax.set_facecolor("#404040")
            ax.set_zlim(-lim, lim)
            for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
                axis.set_pane_color("#323232")
            style = {"arrow_length_ratio": 0.1, "linewidth": 2}
        else:
            ax = fig.add_subplot()
            ax.set_facecolor("#323232")
            ax.axhline(0, color="#858585", linewidth=1)
            ax.axvline(0, color="#858585", linewidth=1)
            ax.grid(True, color="#1F1F28", alpha=0.5)
            ax.set_aspect("equal")
            style = {"angles": "xy", "scale_units": "xy", "scale": 1}
            
        for i, (v, c) in enumerate(zip(vectors, coords)):
            ax.quiver(*[0] * len(c), *c, color=colors[i % len(colors)], label=str(v), **style)

        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.tick_params(colors="white")
        legend = ax.legend(loc="upper left", frameon=False, fontsize="small")
        for text in legend.get_texts():
            text.set_color("white")
        return fig