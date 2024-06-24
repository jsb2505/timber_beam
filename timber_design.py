from timber_beam import TimberBeam
from timber_material import TimberMaterial

class TimberDesign(TimberBeam):
    def __init__(self,
                 length: float,
                 breadth: float,
                 height: float,
                 timber_material_instance: TimberMaterial,
                 effective_length_factor: float = 1.0):
        super().__init__(
            length,
            breadth,
            height,
            timber_material_instance,
            effective_length_factor)

    def get_auto_designed_timber_size_list(self,
                                           load_duration: str,
                                           is_load_sharing: bool,
                                           permanent_udl: float,
                                           imposed_udl: float,
                                           imposed_combination_factor: float,
                                           deflection_limit: float,
                                           is_restrained: bool = True,
                                           permanent_load_factor: float = 1.35,
                                           variable_load_factor: float = 1.5,
                                           with_creep: bool = True
                                           ):
        '''Auto designs timber beam size to smallest depth 
        through a list of standard breadths & depths.

        Input permanent udl in [kN/m] excluding selfweight
        '''
        match self.material.material_type:
            case "softwood":
                breadths = [38, 47, 63, 75]
                heights = [75, 100, 120, 150, 175, 200, 225, 250, 300]
            case "hardwood":
                breadths = [38, 52, 63, 75, 100, 125, 150]
                heights = [50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300]
            case "glulam":
                breadths = [65, 90, 115, 140, 165, 190]
                heights = [225, 270, 315, 360, 405, 450, 495, 540, 585, 630, 675]
            case "lvl":
                breadths = [27, 33, 39, 45, 51, 57, 63, 75]
                heights = [200, 260, 300, 360, 400, 450, 500, 600, 900, 1800]
            case "green_oak":
                breadths = [50, 75, 100, 125, 150, 175, 200, 225, 250]
                heights = [100, 125, 150, 175, 200, 225, 250, 275, 300]
            case _:
                raise ValueError("Unsupported material type. "+
                                 f"Supported types: {self.material.VALID_MATERIALS}")

        for height in heights:
            self.height = height
            for breadth in breadths:
                self.breadth = breadth
                selfweight = self.get_beam_selfweight_per_m()
                permanent_udl += selfweight
                bending_ur = self.get_bending_utilisation(
                    permanent_udl,
                    imposed_udl,
                    permanent_load_factor,
                    variable_load_factor,
                    is_load_sharing,
                    load_duration)
                shear_ur = self.get_shear_utilisation(
                    permanent_udl,
                    imposed_udl,
                    permanent_load_factor,
                    variable_load_factor,
                    is_load_sharing,
                    load_duration)
                ltb_ur = self.get_lateral_torsional_buckling_utilisation(
                    permanent_udl,
                    imposed_udl,
                    permanent_load_factor,
                    variable_load_factor,
                    is_load_sharing,
                    load_duration,
                    is_restrained)
                deflection_ur = self.get_final_deflection_utilisation(
                    permanent_udl,
                    imposed_udl,
                    with_creep,
                    imposed_combination_factor,
                    deflection_limit
                )
                results = {
                    "breadth": self.breadth,
                    "height": self.height,
                    "bending_UR": bending_ur,
                    "shear_UR": shear_ur,
                    "LTB_UR": ltb_ur,
                    "deflection_UR": deflection_ur
                }
                if bending_ur <= 1 and shear_ur <= 1 and ltb_ur <= 1 and deflection_ur <= 1:
                    return results
        return results

    def get_bending_utilisation(self,
                                permanent_udl,
                                imposed_udl,
                                permanent_load_factor,
                                variable_load_factor,
                                is_load_sharing,
                                load_duration
                                ) -> float:
        design_moment = self.get_design_bending_moment(permanent_udl,
                                                       imposed_udl,
                                                       permanent_load_factor,
                                                       variable_load_factor)
        bending_stress = self.get_bending_stress(design_moment)
        bending_strength = self.get_bending_strength(is_load_sharing, load_duration)
        return bending_stress / bending_strength

    def get_shear_utilisation(self,
                              permanent_udl,
                              imposed_udl,
                              permanent_load_factor,
                              variable_load_factor,
                              is_load_sharing,
                              load_duration
                              ) -> float:
        design_shear = self.get_design_shear_force(permanent_udl,
                                                   imposed_udl,
                                                   permanent_load_factor,
                                                   variable_load_factor)
        shear_stress = self.get_shear_stress(design_shear)
        shear_strength = self.get_shear_strength(is_load_sharing, load_duration)
        return shear_stress / shear_strength

    def get_lateral_torsional_buckling_utilisation(
            self,
            permanent_udl,
            imposed_udl,
            permanent_load_factor,
            variable_load_factor,
            is_load_sharing,
            load_duration,
            is_restrained
            ) -> float:
        design_moment = self.get_design_bending_moment(permanent_udl,
                                                       imposed_udl,
                                                       permanent_load_factor,
                                                       variable_load_factor)
        bending_stress = self.get_bending_stress(design_moment)
        if is_restrained or self.breadth >= self.height:
            lateral_torsional_buckling_utilisation_ratio = None
        else:
            buckling_strength = self.get_buckling_strength(is_load_sharing, load_duration)
            lateral_torsional_buckling_utilisation_ratio = bending_stress / buckling_strength
        return lateral_torsional_buckling_utilisation_ratio

    def get_final_deflection_utilisation(
            self,
            permanent_udl,
            imposed_udl,
            with_creep,
            imposed_combination_factor,
            deflection_limit
            ) -> float:
        final_deflection = self.get_final_deflection(permanent_udl,
                                                     imposed_udl,
                                                     imposed_combination_factor,
                                                     with_creep
                                                     )
        return final_deflection / deflection_limit

'''
Get_Auto_Designed_Timber_Size_Depth = LAMBDA(
    Auto designs timber beam size to smallest depth for a given breadth
    service_class,
    load_duration,
    load_sharing_bool,
    strength_class,
    material,
    permanent_UDL,
    imposed_UDL,
    restrained_bool,
    length_mm,
    effective_length_factor,
    imposed_combination_factor,
    deflection_limit,
    breadth,
    [height],
    LET(
        L, length_mm,
        K_ef, effective_length_factor,
        ϕ_2, imposed_combination_factor,
        δ_lim, deflection_limit,
        L_ef, K_ef * L,
        b, breadth,
        h, IF(ISOMITTED(height), 75, height),
        g_swt, Get_Beam_Selfweight_per_m(b, h, material, strength_class),
        g_k, permanent_UDL,
        g_kt, SUM(g_k, g_swt),
        q_k, imposed_UDL,
        h_next, h + 5, # change value of iteration here
        
        # Bending
        design_moment_kNm, Loading.Get_Design_Bending_Moment(g_kt, q_k, L),
        bending_stress, Get_Bending_Stress(b, h, material, design_moment_kNm),
        bending_strength, Get_Bending_Strength(
            h,
            material,
            strength_class,
            service_class,
            load_sharing_bool,
            load_duration
        ),
        bending_UR, bending_stress / bending_strength,
        
        # Shear
        shear_strength, Get_Shear_Strength(
            material,
            strength_class,
            service_class,
            load_sharing_bool,
            load_duration
        ),
        design_shear_kN, Loading.Get_Design_Shear_Force(g_kt, q_k, L),
        shear_stress, Get_Shear_Stress(design_shear_kN, b, h, material),
        shear_UR, shear_stress / shear_strength,
        
        # LTB
        buckling_strength, Get_Buckling_Strength(
            b,
            h,
            L_ef,
            material,
            strength_class,
            bending_strength
        ),
        LTB_UR, IF(OR(b >= h, restrained_bool), "Not Req'd", bending_stress / buckling_strength),
        #
        buckling_strength_next, Get_Buckling_Strength(
            b,
            h + 5,
            L_ef,
            material,
            strength_class,
            bending_strength
        ),
        LTB_UR_next, IF(
            OR(b >= h, restrained_bool),
            "Not Req'd",
            bending_stress / buckling_strength_next
        ),
        
        # Deflection
        δ_fin, Get_Final_Deflection(
            g_kt,
            q_k,
            L,
            material,
            strength_class,
            b,
            h,
            service_class,
            ϕ_2
        ),
        δ_UR, δ_fin / δ_lim,
        #
        results, MAKEARRAY(6, 1, LAMBDA(r, c, CHOOSE(r, b, h, bending_UR, shear_UR, LTB_UR, δ_UR))),
        #
        IF(
            AND(bending_UR < 1, shear_UR < 1, δ_UR < 1),
            IF(
                OR(restrained_bool, LTB_UR = "Not Req'd"),
                results,
                IF(
                    OR(LTB_UR < 1, LTB_UR_next > LTB_UR), # as h increases LTB gets worse
                    results,
                    Get_Auto_Designed_Timber_Size_Depth(
                        service_class,
                        load_duration,
                        load_sharing_bool,
                        strength_class,
                        material,
                        g_k,
                        q_k,
                        restrained_bool,
                        L,
                        K_ef,
                        ϕ_2,
                        δ_lim,
                        b,
                        h_next
                    )
                )
            ),
            Get_Auto_Designed_Timber_Size_Depth(
                service_class,
                load_duration,
                load_sharing_bool,
                strength_class,
                material,
                g_k,
                q_k,
                restrained_bool,
                L,
                K_ef,
                ϕ_2,
                δ_lim,
                b,
                h_next
            )
        )
    )
);

/**
Auto designs timber beam size to smallest breadth for a given depth
*/
Get_Auto_Designed_Timber_Size_Breadth = LAMBDA(
    service_class,
    load_duration,
    load_sharing_bool,
    strength_class,
    material,
    permanent_UDL,
    imposed_UDL,
    restrained_bool,
    length_mm,
    effective_length_factor,
    imposed_combination_factor,
    deflection_limit,
    height,
    [breadth],
    LET(
        L, length_mm,
        K_ef, effective_length_factor,
        ϕ_2, imposed_combination_factor,
        δ_lim, deflection_limit,
        L_ef, K_ef * L,
        h, height,
        b, IF(ISOMITTED(breadth), 40, breadth),
        b_next, b + 5, # change value of iteration here
        g_swt, Get_Beam_Selfweight_per_m(b, h, material, strength_class),
        g_k, permanent_UDL,
        g_kt, SUM(g_k, g_swt),
        q_k, imposed_UDL,
        
        # Bending
        design_moment_kNm, Loading.Get_Design_Bending_Moment(g_kt, q_k, L),
        bending_stress, Get_Bending_Stress(b, h, material, design_moment_kNm),
        bending_strength, Get_Bending_Strength(
            h,
            material,
            strength_class,
            service_class,
            load_sharing_bool,
            load_duration
        ),
        bending_UR, bending_stress / bending_strength,
        
        # Shear
        shear_strength, Get_Shear_Strength(
            material,
            strength_class,
            service_class,
            load_sharing_bool,
            load_duration
        ),
        design_shear_kN, Loading.Get_Design_Shear_Force(g_kt, q_k, L),
        shear_stress, Get_Shear_Stress(design_shear_kN, b, h, material),
        shear_UR, shear_stress / shear_strength,
        
        # LTB
        buckling_strength, Get_Buckling_Strength(
            b,
            h,
            L_ef,
            material,
            strength_class,
            bending_strength
        ),
        LTB_UR, IF(OR(b >= h, restrained_bool), "Not Req'd", bending_stress / buckling_strength),
        
        # Deflection
        δ_fin, Get_Final_Deflection(
            g_kt,
            q_k,
            L,
            material,
            strength_class,
            b,
            h,
            service_class,
            ϕ_2
        ),
        δ_UR, δ_fin / δ_lim,
        #
        results, MAKEARRAY(6, 1, LAMBDA(r, c, CHOOSE(r, b, h, bending_UR, shear_UR, LTB_UR, δ_UR))),
        #
        IF(
            AND(bending_UR < 1, shear_UR < 1, δ_UR < 1),
            IF(
                OR(restrained_bool, LTB_UR = "Not Req'd"),
                results,
                IF(
                    LTB_UR < 1,
                    results,
                    Get_Auto_Designed_Timber_Size_Breadth(
                        service_class,
                        load_duration,
                        load_sharing_bool,
                        strength_class,
                        material,
                        g_k,
                        q_k,
                        restrained_bool,
                        L,
                        K_ef,
                        ϕ_2,
                        δ_lim,
                        h,
                        b_next
                    )
                )
            ),
            Get_Auto_Designed_Timber_Size_Breadth(
                service_class,
                load_duration,
                load_sharing_bool,
                strength_class,
                material,
                g_k,
                q_k,
                restrained_bool,
                L,
                K_ef,
                ϕ_2,
                δ_lim,
                h,
                b_next
            )
        )
    )
)
'''