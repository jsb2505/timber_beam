from math import sqrt, pi, log
from timber_material import TimberMaterial
from timber_beam import TimberBeam


class TimberJoist(TimberBeam):

    ALLOWABLE_SOFTWOOD_GRADES = ["C16", "C24"]

    def __init__(self,
                 joist_length: float,
                 floor_width: float,
                 breadth: float,
                 height: float,
                 softwood_grade: str = "C24",
                 ):
        if softwood_grade not in self.ALLOWABLE_SOFTWOOD_GRADES:
            raise ValueError(f"Softwood grade not supported: '{softwood_grade}'. "+
                             f"Allowable softwood grades: {self.ALLOWABLE_SOFTWOOD_GRADES}")
        super().__init__(
            joist_length,
            breadth,
            height,
            TimberMaterial("softwood", softwood_grade, 1)
            )
        self._floor_width = None
        self.floor_width = floor_width

    @property
    def floor_width(self) -> float:
        '''Returns the floor width in [mm].'''
        return self._floor_width

    @floor_width.setter
    def floor_width(self, new_floor_width: float) -> None:
        '''Input floor width in [mm]'''
        if new_floor_width <= 0:
            raise ValueError(f"Floor width, {new_floor_width}mm, must be positive.")
        self._floor_width = new_floor_width

    def get_constant_for_unit_impulse_velocity(self) -> float:
        '''Returns the limiting value of 'b' used to check
        the unit impulse velocity response criterion.
        
        Ref: EC5 Eq (7.4) and Table NA.6
        '''
        a_limit = self.get_deflection_limit_for_1kn_point_load()
        return 180 - 60*a_limit if a_limit <= 1 else 160 - 40*a_limit

    def get_deflection_limit_for_1kn_point_load(self) -> float:
        '''Returns the limiting value of 'a' used to check
        the instanteous vertical deflection criterion.
        
        'a' is the deflection limit in [mm] for the joist under a 1kN point load.
        'a' is also used to find limiting value of 'b'.
        Ref: EC5 EC5 Eq (7.3) and Table NA.6
        '''
        return 1.8 if self.length <= 4000 else 16500 / self.length**1.1

    def get_fundamental_frequency(self,
                                  joist_stiffness_per_metre: float,
                                  mass_of_floor_per_unit_area: float
                                  ) -> float:
        '''Returns the fundamental frequency in units of [Hz].

        Input:
            mass of floor per unit area in units [kg/m^2].
            joist stiffness per metre in units [Nmm^2/m].
        
        The mass should include the selfweight of the joist, floor board and plasterboard.
        The stiffness should be the flexural stiffness of the joist only (EI) / joist spacing.
        '''
        joist_length = self.length / 10**3
        joist_stiffness_per_metre = joist_stiffness_per_metre / 10**6
        return (pi / (2 * joist_length**2)) * sqrt(joist_stiffness_per_metre / mass_of_floor_per_unit_area)

    def get_impulse_velocity_limit(self,
                                   fundamental_frequency: float,
                                   modal_damping_ratio: float
                                   ) -> float:
        '''Returns the limit for the unit impulse velocity criterion.'''
        b_limit = self.get_constant_for_unit_impulse_velocity()
        return b_limit**(fundamental_frequency*modal_damping_ratio - 1)

    def get_impulse_velocity_response(self,
                                      n_40: float,
                                      mass_of_floor_per_unit_area: float,
                                      ) -> float:
        '''Returns the impulse velocity reponse, Nu, in units [m/Ns^2].
        
        i.e. the maximum initial value of the vertical floor vibration velocity (in m/s)
        caused by an ideal unit impulse (1 Ns) applied at the point of the
        floor giving maximum response. Components above 40 Hz may be disregarded.

        Input:
            mass of floor per unit area in units [kg/m^2].
            The mass should include the selfweight of the joist, floor board and plasterboard.
        '''
        floor_width = self.floor_width / 10**3
        floor_span = self.length / 10**3
        return (4 * (0.4 + 0.6 * n_40)) / (mass_of_floor_per_unit_area * floor_width * floor_span + 200)

    def get_instanteous_deflection_under_point_load(self,
                                                    k_dist: float,
                                                    k_amp: float,
                                                    equivalent_length: float,
                                                    joist_stiffness: float
                                                    ) -> float:
        return (1000 * k_dist * equivalent_length**3 * k_amp) / (48 * joist_stiffness)
    
    def get_number_of_first_order_modes(self,
                                        mass_of_floor_per_unit_area: float,
                                        floor_stiffness_per_metre: float,
                                        joist_stiffness_per_metre: float
                                        ) -> float:
        '''Returns the number of first order modes, n_40, upto 40 Hz.
        
        Input:
            mass of floor per unit area in units [kg/m^2].
            joist stiffness per metre in units [Nmm^2/m].
            floor stiffness per metre in units [Nmm^2/m].

        The floor stiffness is the floor plate stiffness in an axis perpendicular to
        the axis of the joist. It should include the decking and may the plasterboard.
        For open-webbed joists with transverse stiffnesses these may be included.

        Ref: EC5 Eq (7.7) and NA.2.7.2
        '''
        floor_width = self.floor_width / 10**3
        floor_span = self.length / 10**3
        fundamental_frequency = self.get_fundamental_frequency(joist_stiffness_per_metre, mass_of_floor_per_unit_area)
        floor_stiffness_per_metre = floor_stiffness_per_metre / 10**6
        joist_stiffness_per_metre = joist_stiffness_per_metre / 10**6
        return (((40 / fundamental_frequency)**2 - 1)
                * (floor_width / floor_span)**4
                * (joist_stiffness_per_metre / floor_stiffness_per_metre))**0.25

    def get_k_dist(self,
                   floor_stiffness_per_metre: float,
                   joist_spacing: float = 400,
                   is_strutted: bool = True
                   ) -> float:
        '''Returns k_dist used for finding the instantaneous deflection under variable load.
        
        Input:
            joist spacing in [mm].
            floor stiffness per metre in units [Nmm^2/m].

        The floor stiffness is the floor plate stiffness in an axis perpendicular to
        the axis of the joist. It should include the decking and may the plasterboard.
        For open-webbed joists with transverse stiffnesses these may be included.

        Ref: EC5 NA.2.7.2
        '''
        k_strut = self.material.get_k_strut(is_strutted)
        return max(0.3,
                   k_strut * (0.38 - 0.08 * log((14 * floor_stiffness_per_metre) / joist_spacing**4))
                   )

    @staticmethod
    def get_k_amp(joist_type_index: int = 0):
        '''Returns k_amp.
        
        k_amp is an amplification factor to account for shear deflections
        in the case of solid timber and glued thin-webbed joists or joint
        slip in the case of mechanically-jointed floor trusses.

        Input joist_type_index:
            0, for solid timber joists
            1, for glued thin-webbed joists
            2, for mechanically jointed floor trusses
        '''
        if joist_type_index == 0:
            k_amp = 1.05
        elif joist_type_index == 1:
            k_amp = 1.2
        elif joist_type_index == 2:
            k_amp = 1.3
        else:
            raise ValueError(f"Incorrect joist type index :'{joist_type_index}'. "+
                             "Supported joist type indices: 0, for solid timber joists, "+
                             "1, for glued thin-webbed joists, "+
                             "2, for mechanically jointed floor trusses.")
        return k_amp

    def get_max_trimmer_span(self,
                             span_of_joists_on_to_trimmer: float,
                             ) -> float:
        '''Returns the max span of the doubled up trimmer joist.
        
        The breadth is for the single trimmer so the total breadth
        is twice this value as they must be doubled up.
        '''
        coefficient_for_grade = 1.075 if self.material.strength_grade == "C24" else 1
        return (0.165
                * (-0.308 * span_of_joists_on_to_trimmer / 1000 + 3.38)
                * (0.0214 * self.breadth + 1.12)
                * (0.0149 * self.height - 0.073)
                * 1000
                * coefficient_for_grade
                )

    def get_max_trimming_joist_span(self,
                                    span_of_trimmed_joists_onto_trimmer: float,
                                    span_of_supported_trimmer_beam: float,
                                    ) -> float:
        '''Returns the max span of the doubled up trimming joist which supports a trimmer.
        
        The breadth is for the single trimming joist so the total breadth
        is twice this value as they must be doubled up.
        '''
        coefficient_for_grade = 1.075 if self.material.strength_grade == "C24" else 1
        return (0.032
                * (-0.31 * span_of_supported_trimmer_beam / 1000 + 3.8)
                * (-1.52 * span_of_trimmed_joists_onto_trimmer / self.length + 3.93)
                * (0.022 * self.breadth + 1.79)
                * (0.0196 * self.height - 0.16)
                * 1000
                * coefficient_for_grade
                )
