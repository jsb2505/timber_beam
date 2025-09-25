from math import sqrt, pi
from timber_section import TimberSection
from timber_material import TimberMaterial


class TimberBeam(TimberSection):
    def __init__(self,
                 length: float,
                 breadth: float,
                 height: float,
                 timber_material_instance: TimberMaterial,
                 effective_length_factor: float = 1.0
                 ):
        super().__init__(breadth, height, timber_material_instance)
        self._length = None
        self._effective_length_factor = 1.0
        self._effective_length = None
        self.length = length
        self.effective_length_factor = effective_length_factor

    @property
    def length(self) -> float:
        '''Returns the actual beam length in [mm].'''
        return self._length

    @length.setter
    def length(self, new_length: float) -> None:
        '''Input length in [mm]'''
        if new_length <= 0:
            raise ValueError(f"Length, {new_length}mm, must be positive.")
        self._length = new_length
        self._set_effective_length()

    @property
    def effective_length_factor(self) -> float:
        return self._effective_length_factor

    @effective_length_factor.setter
    def effective_length_factor(self, new_effective_length_factor: float) -> None:
        if new_effective_length_factor <= 0:
            raise ValueError(f"Effective length factor, {new_effective_length_factor}, "+
                             " must be positive.")
        self._effective_length_factor = new_effective_length_factor
        self._set_effective_length()

    @property
    def effective_length(self) -> float:
        '''Returns effective length in [mm].'''
        return self._effective_length_factor

    def _set_effective_length(self) -> None:
        self._effective_length_factor = self.length * self.effective_length_factor

    def get_beam_selfweight_per_m(self) -> float:
        '''Returns beam selfweight in [kN/m].'''
        density_mean = self.material.material_properties["density_mean"]
        return density_mean * (self.breadth / 1000) * (self.height / 1000) * (9.81 / 1000)

    def get_shear_stress(self, design_shear: float) -> float:
        '''Input design shear force in [kN].'''
        k_cr = self.material.get_k_cr()
        return (3 * design_shear * 10**3) / (2 * self.area * k_cr)

    def get_shear_strength(self, is_load_sharing: bool, load_duration: str) -> float:
        gamma_m = self.material.get_gamma_factor()
        k_sys = self.material.get_k_sys(is_load_sharing)
        k_mod = self.material.get_k_mod(load_duration)
        f_v_k = self.material.material_properties["f_v_k"]
        return k_mod * k_sys * f_v_k / gamma_m

    def get_bending_stress(self, design_moment: float) -> float:
        '''Input design moment in [kNm].'''
        elastic_section_modulus_major = self.get_elastic_section_modulus(True)
        return design_moment * 10**6 / elastic_section_modulus_major

    def get_critical_bending_stress(self) -> float:
        '''Ref: EC5 Eq 6.31'''
        e_005 = self.material.material_properties["E_005"]
        inertia_minor = self.get_second_moment_of_area(False)
        inertia_torsional = self.get_torsional_moment_of_inertia()
        g_005 = self.get_g_005()
        elastic_section_modulus_major = self.get_elastic_section_modulus(True)
        return ((pi / (self.effective_length * elastic_section_modulus_major))
                * (sqrt(e_005 * inertia_minor * g_005 * inertia_torsional)))

    def get_relative_slenderness(self) -> float:
        sigma_m_crit = self.get_critical_bending_stress()
        f_m_y_k = self.material.material_properties["f_m_y_k"]
        return sqrt(f_m_y_k / sigma_m_crit)

    def get_bending_strength(self, is_load_sharing: bool, load_duration: str) -> float:
        gamma_m = self.material.get_gamma_factor()
        k_sys = self.material.get_k_sys(is_load_sharing)
        k_mod = self.material.get_k_mod(load_duration)
        k_h = self.material.get_k_h(self.height)
        f_m_y_k = self.material.material_properties["f_m_y_k"]
        return k_h * k_mod * k_sys * f_m_y_k / gamma_m

    def get_buckling_strength(self, is_load_sharing: bool, load_duration: str) -> float:
        bending_strength = self.get_bending_strength(is_load_sharing, load_duration)
        relative_slenderness = self.get_relative_slenderness()
        k_crit = self.material.get_k_crit(relative_slenderness)
        return k_crit * bending_strength

    def get_bearing_stress(self, bearing_length: float, design_shear_force: float) -> float:
        '''Input:
            bearing length in [mm]
            design shear force in [kN]
        '''
        bearing_area = self.breadth * bearing_length
        return design_shear_force * 1000 / bearing_area

    def get_bearing_strength(self, load_duration: str, bearing_support_condition: int) -> float:
        '''bearing_support_condition can be 0, 1 or 2:
            0 = no bearing enhancement support
            1 = bearing enhanced: continuous support
            2 = bearing enhanced: discrete support'''
        gamma_m = self.material.get_gamma_factor()
        k_mod = self.material.get_k_mod(load_duration)
        k_c_90 = self.material.get_k_c_90(bearing_support_condition)
        f_c_90_k = self.material.material_properties["f_c_90_k"]
        return k_c_90 * k_mod * f_c_90_k / gamma_m

    def get_flexural_deflection(self,
                                uniformly_distributed_load: float,
                                imposed_combination_factor: float,
                                with_creep: bool = True
                                ) -> float:
        '''Returns the max flexural deflection from a UDL.

        Input:
            uniformly distributed load in [kN/m].
            for a permanent udl, the imposed combination factor should be 1.
        '''
        udl = uniformly_distributed_load
        psi_2 = imposed_combination_factor
        if with_creep:
            k_def = self.material.get_k_def()
        else:
            k_def = 0
        e_0_mean = self.material.material_properties["E_0_mean"]
        inertia_major = self.get_second_moment_of_area(True)
        return ((5 * udl * self.length**4) / (384 * e_0_mean * inertia_major)) * (1 + psi_2 * k_def)

    def get_shear_deflection(self,
                             uniformly_distributed_load: float,
                             imposed_combination_factor: float,
                             with_creep: bool = True
                             ) -> float:
        '''Returns the max shear deflection from a UDL.

        Input:
            uniformly distributed load in [kN/m].
            for a permanent udl, the imposed combination factor should be 1.
        '''
        udl = uniformly_distributed_load
        psi_2 = imposed_combination_factor
        k_form = self.material.get_k_form()
        if with_creep:
            k_def = self.material.get_k_def()
        else:
            k_def = 0
        g_mean = self.material.material_properties["G_mean"]
        return ((k_form * udl * self.length**2) / (8 * g_mean * self.area)) * (1 + psi_2 * k_def)

    def get_design_bending_moment(self,
                                  permanent_udl: float,
                                  imposed_udl: float,
                                  permanent_load_factor: float = 1.35,
                                  variable_load_factor: float = 1.5
                                  ) -> float:
        return ((permanent_load_factor * permanent_udl
                 + variable_load_factor * imposed_udl)
                * (self.length / 1000)**2 / 8)

    def get_design_shear_force(self,
                               permanent_udl: float,
                               imposed_udl: float,
                               permanent_load_factor: float = 1.35,
                               variable_load_factor: float = 1.5
                               ) -> float:
        return ((permanent_load_factor * permanent_udl
                 + variable_load_factor * imposed_udl)
                * (self.length / 1000) / 2)

    def get_final_deflection(self,
                             permanent_udl: float,
                             imposed_udl: float,
                             imposed_combination_factor: float = 0.3,
                             with_creep: bool = True
                             ) -> float:
        '''Returns the max final deflection from a UDL.

        Input uniformly distributed loads in [kN/m].
        '''
        delta_flex_g = self.get_flexural_deflection(permanent_udl, 1, with_creep)
        delta_flex_q = self.get_flexural_deflection(imposed_udl, imposed_combination_factor, with_creep)
        delta_v_g = self.get_shear_deflection(permanent_udl, 1, with_creep)
        delta_v_q = self.get_shear_deflection(imposed_udl, imposed_combination_factor, with_creep)
        return sum([delta_flex_g, delta_flex_q, delta_v_g, delta_v_q])
