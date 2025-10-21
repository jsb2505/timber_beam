import json
from math import sqrt


class TimberMaterial():

    VALID_MATERIALS = ["softwood", "hardwood", "glulam", "lvl", "green_oak"]
    VALID_SERVICE_CLASSES = [1, 2, 3]
    LOAD_DURATIONS = ["permanent", "long_term", "medium_term", "short_term", "instantaneous"]

    def __init__(self,
                 material_type: str,
                 strength_grade: str,
                 service_class: int
                 ):
        self._type = None
        self._strength_grade = None
        self._material_properties = None
        self._service_class = None
        self.service_class = service_class
        self.set_material(material_type, strength_grade)

    @property
    def material_type(self) -> str:
        '''Returns the timber material type.'''
        return self._type

    @property
    def strength_grade(self) -> int:
        '''Returns the timber strength grade.'''
        return self._strength_grade

    @property
    def material_properties(self) -> dict:
        return self._material_properties

    def set_material(self, material_type: str = "softwood", strength_grade: str = "C24") -> None:
        material_type = material_type.strip().lower()
        strength_grade.strip().upper()
        if material_type in self.VALID_MATERIALS:
            file_name = material_type + "_data.json"
            with open(file_name, encoding='utf-8') as f:
                timber_data_dict = json.load(f)
        else:
            raise ValueError(f"Material type, {material_type}, not valid. "+
                             f"Valid material types: {self.VALID_MATERIALS}.")
        if strength_grade in timber_data_dict:
            material_properties = timber_data_dict[strength_grade]
        else:
            raise ValueError(f"Strength grade '{strength_grade}', not found. "+
                             f"Strength grades in database: {timber_data_dict.keys()}.")
        self._material_properties = material_properties
        self._strength_grade = strength_grade
        self._type = material_type

    @property
    def service_class(self) -> int:
        return self._service_class

    @service_class.setter
    def service_class(self, new_service_class: int) -> None:
        if not self.is_valid_service_class(new_service_class):
            raise ValueError(f"Service class, {new_service_class}, is not valid. " +
                             f"Valid service classes: {self.VALID_SERVICE_CLASSES}.")
        self._service_class = new_service_class

    @classmethod
    def is_valid_service_class(cls, service_class: int) -> bool:
        return service_class in cls.VALID_SERVICE_CLASSES

    @classmethod
    def is_valid_material_type(cls, material_type: str) -> bool:
        return material_type in cls.VALID_MATERIALS

    def get_gamma_factor(self) -> float:
        if self.material_type in ["softwood", "hardwood", "green_oak"]:
            gamma_factor = 1.3
        elif self.material_type == "glulam":
            gamma_factor = 1.25
        elif self.material_type == "lvl":
            gamma_factor = 1.2
        return gamma_factor

    def get_k_c_90(self, bearing_support_condition: int = 0) -> float:
        '''
        bearing_support_condition can be 0, 1 or 2
            0 = no bearing enhancement support
            1 = bearing enhanced: continuous support
            2 = bearing enhanced: discrete support
        '''
        # only softwood or glulam get bearing support enhancement
        if (bearing_support_condition == 0
            or self.material_type not in ["softwood", "glulam"]):
            k_c_90 = 1.0
        elif bearing_support_condition == 1:
            if self.material_type == "softwood":
                k_c_90 = 1.25
            else:  # is glulam
                k_c_90 = 1.5
        elif bearing_support_condition == 2:
            if self.material_type == "softwood":
                k_c_90 = 1.5
            else:  # is glulam
                k_c_90 = 1.75
        else:
            raise ValueError(f"Invalid bearing support condition index, {bearing_support_condition}. " +
                             "Valid integers: 0 = no bearing enhancement support, "+
                             "1 = bearing enhanced: continuous support, " +
                             "2 = bearing enhanced: discrete support.")
        return k_c_90

    @staticmethod
    def get_k_strut(is_strutted: bool = False) -> float:
        if is_strutted:
            return 0.97
        return 1.0

    def get_k_n(self) -> float:
        if self.material_type in ["softwood", "hardwood", "green_oak"]:
            k_n = 5.0
        elif self.material_type == "glulam":
            k_n = 6.5
        elif self.material_type == "lvl":
            k_n = 4.5
        return k_n

    def get_k_form(self) -> float:
        return 1.2

    def get_k_mod(self, load_duration: str) -> float:
        k_mods_index = self.service_class - 1
        load_duration = load_duration.strip().lower()
        if load_duration not in self.LOAD_DURATIONS:
            raise ValueError(f"Load duration '{load_duration}' is invalid. "+
                             f"Valid load durations: {self.LOAD_DURATIONS}.")
        load_duration_index = self.LOAD_DURATIONS.index(load_duration)
        k_mods_service_class_1 = [0.6, 0.7, 0.8, 0.9, 1.1]
        k_mods_service_class_2 = [0.6, 0.7, 0.8, 0.9, 1.1]
        k_mods_service_class_3 = [0.5, 0.55, 0.65, 0.7, 0.9]
        k_mods_array = [k_mods_service_class_1, k_mods_service_class_2, k_mods_service_class_3]
        k_mods = k_mods_array[k_mods_index]
        return k_mods[load_duration_index]

    def get_k_def(self) -> float:
        '''Returns the modification factor for deflection.'''
        k_def_index = self.service_class - 1
        if self.material_type in ["softwood", "hardwood", "glulam", "lvl"]:
            k_defs = [0.6, 0.8, 2]
        elif self.material_type == "green_oak":
            k_defs = [1.6, 1.8, 2]
        return k_defs[k_def_index]

    def get_k_h(self, height: float) -> float:
        if self.material_type in ["softwood", "hardwood", "green_oak"]:
            if height <= 150:
                k_h = min((150 / height)**0.2, 1.3)
            else:
                k_h = 1
        elif self.material_type == "glulam":
            if height <= 600:
                k_h = min((600 / height)**0.1, 1.1)
            else:
                k_h = 1
        elif self.material_type == "lvl":
            # size effect factor for LVL is declared by the manufacturer
            size_factor = self.material_properties.get("size_factor", 0.12)
            if size_factor is None:
                size_factor = 0.12
            k_h = min((300 / height)**size_factor, 1.2)
        return k_h

    @staticmethod
    def get_k_sys(is_load_sharing: bool) -> float:
        return 1.1 if is_load_sharing else 1.0

    def get_k_cr(self) -> float:
        if self.material_type in ["softwood", "hardwood", "green_oak", "glulam"]:
            k_cr = 0.67
        else:
            k_cr = 1.0
        return k_cr

    @staticmethod
    def get_k_crit(relative_slenderness) -> float:
        if relative_slenderness <= 0.75:
            k_crit = 1
        elif relative_slenderness <= 1.4:
            k_crit = 1.56 - 0.75 * relative_slenderness
        else:
            k_crit = 1 / relative_slenderness**2
        return k_crit

    def get_k_v(self,
                height: float,
                notch_depth: float,
                bearing_length: float,
                distance_to_notch_from_edge_of_support: float,
                is_bottom_notched: bool,
                length_of_sloping_notch: float = 0
                ) -> float:
        '''Returns the notch shear strength reduction factor.'''
        effective_height = height - notch_depth
        if is_bottom_notched:
            distance_to_notch = (bearing_length / 2) + distance_to_notch_from_edge_of_support
        else:  # top notched
            distance_to_notch = distance_to_notch_from_edge_of_support

        if is_bottom_notched:
            k_n = self.get_k_n()
            alpha = self.get_notch_ratio(height, notch_depth)
            k_v = min(1,
                      (k_n * (1 + 1.1*(length_of_sloping_notch / (height - effective_height))**1.5 / sqrt(height)))
                      / (sqrt(height) * (sqrt(alpha * (1-alpha)) + 0.8 * distance_to_notch * sqrt((1 / alpha) - alpha**2) / height))
                )
        else:  # top notched
            k_v = 1
            # Possible enhancement strength enhancement possible if using BS 5268-2, Cl 2.10.4
            # if distance_to_notch > effective_height:
            #     k_v = 1
            # else:
            #     k_v = (height * (effective_height - distance_to_notch)
            #            + (distance_to_notch * effective_height)) / effective_height**2
        return k_v

    @staticmethod
    def get_notch_ratio(height: float, notch_depth: float) -> float:
        '''Returns the notch depth ratio known as alpha.'''
        return (height - notch_depth) / height
