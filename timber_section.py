from timber_material import TimberMaterial


class TimberSection():
    def __init__(self,
                 breadth: float,
                 height:float,
                 material: TimberMaterial):
        self.material = material
        self._breadth = 1
        self._height = 1
        self._area = None
        self.breadth = breadth
        self.height = height

    @property
    def breadth(self) -> float:
        '''Returns the breadth of the rectangular timber section in [mm].'''
        return self._breadth

    @breadth.setter
    def breadth(self, new_breadth: float) -> None:
        '''Input breadth in [mm].'''
        if new_breadth <= 0:
            raise ValueError(f"Breadth, {new_breadth}mm, must be positive.")
        self._breadth = new_breadth
        self._set_area()

    @property
    def height(self) -> float:
        '''Returns the height of the rectangular timber section in [mm].'''
        return self._height

    @height.setter
    def height(self, new_height: float) -> None:
        '''Input height in [mm].'''
        if new_height <= 0:
            raise ValueError(f"Height, {new_height}mm, must be positive.")
        self._height = new_height
        self._set_area()

    @property
    def area(self) -> float:
        '''Returns the cross-sectional area of the 
        rectangular timber section in [mm^2].'''
        return self._area

    def _set_area(self) -> None:
        '''Private setter to update the area attribute when breadth or height is changed.'''
        self._area = self.breadth * self.height

    def get_second_moment_of_area(self, is_major_axis: bool = True) -> float:
        if is_major_axis:
            return self.breadth * self.height**3 / 12
        return self.height * self.breadth**3 /12

    def get_elastic_section_modulus(self, is_major_axis: bool = True) -> float:
        if is_major_axis:
            return self.breadth * self.height**2 / 6
        return self.height * self.breadth**2 /6

    def get_torsion_coefficient_beta(self) -> float:
        '''Aspect ratio coefficient for torsional moment of inertia.
        No exact formulas for non-circular cross-sections exist.
        '''
        long_side = max(self.height, self.breadth)
        short_side = min(self.height, self.breadth)
        return (1/3) - 0.21 * (short_side / long_side) * (1 - (short_side**4) / (12 * long_side**4))

    def get_torsional_moment_of_inertia(self) -> float:
        beta = self.get_torsion_coefficient_beta()
        long_side = max(self.height, self.breadth)
        short_side = min(self.height, self.breadth)
        return beta * long_side * short_side**3

    def get_g_005(self) -> float:
        '''5th percentile shear modulus derived from EC5 Eq6.31, Eq6.32 & EN 384'''
        g_005 = self.material.material_properties["G_005"]
        if g_005 is None:
            if self.material.material_type in ["softwood"]:
                beta = self.get_torsion_coefficient_beta()
                # https://blogs.napier.ac.uk/cwst/5th-percentile-shear-modulus/
                alpha = (48 + (2 / 3)) * beta
                e_005 = self.material.material_properties["E_005"]
                g_005 = e_005 / alpha
            elif self.material.material_type in ["hardwood", "green_oak"]:
                e_005 = self.material.material_properties["E_005"]
                g_005 = e_005 / 16
            else:
                raise KeyError("G_005 value is not given and logic to define it is not supported.")
        return g_005
