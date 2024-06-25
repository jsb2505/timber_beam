from timber_beam import TimberBeam


class TimberDesign(TimberBeam):
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

    def _find_utilisation_results(
            self,
            load_duration: str,
            is_load_sharing: bool,
            permanent_udl: float,
            imposed_udl: float,
            imposed_combination_factor: float,
            deflection_limit: float,
            is_restrained: bool = True,
            permanent_load_factor: float = 1.35,
            variable_load_factor: float = 1.5,
            with_creep: bool = True,
            ) -> dict:
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
            "bending_UR": bending_ur,
            "shear_UR": shear_ur,
            "LTB_UR": ltb_ur,
            "deflection_UR": deflection_ur
            }
        return results

    def get_auto_designed_timber_size_list(
            self,
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
                permanent_udl_plus_swt = permanent_udl + selfweight
                ur_results = self._find_utilisation_results(
                    load_duration,
                    is_load_sharing,
                    permanent_udl_plus_swt,
                    imposed_udl,
                    imposed_combination_factor,
                    deflection_limit,
                    is_restrained,
                    permanent_load_factor,
                    variable_load_factor,
                    with_creep
                    )

                passes_checks = True
                for result in ur_results.values():
                    if result is None:
                        continue
                    if result > 1:
                        passes_checks = False
                        break

                if passes_checks:
                    results = {
                        "breadth": self.breadth,
                        "height": self.height,
                        }
                    results.update(ur_results)
                    return results
        # heights and breadths list exhausted returning results from largest section
        results = {
            "breadth": self.breadth,
            "height": self.height,
            }
        results.update(ur_results)
        return results

    def get_auto_designed_timber_size_height(
            self,
            load_duration: str,
            is_load_sharing: bool,
            permanent_udl: float,
            imposed_udl: float,
            imposed_combination_factor: float,
            deflection_limit: float,
            is_restrained: bool = True,
            permanent_load_factor: float = 1.35,
            variable_load_factor: float = 1.5,
            with_creep: bool = True,
            height_iteration = 5,
            starting_height = 100,
            max_height = 600
            ) -> dict:
        '''Auto designs timber beam size to smallest height for a given breadth'''
        self.height = starting_height
        selfweight = self.get_beam_selfweight_per_m()
        permanent_udl_plus_swt = permanent_udl + selfweight
        ur_results = self._find_utilisation_results(
            load_duration,
            is_load_sharing,
            permanent_udl_plus_swt,
            imposed_udl,
            imposed_combination_factor,
            deflection_limit,
            is_restrained,
            permanent_load_factor,
            variable_load_factor,
            with_creep
            )
        ltb_ur = ur_results["LTB_UR"]

        passes_checks = True
        for result in ur_results.values():
            if result is None:
                continue
            if result > 1:
                passes_checks = False
                break

        while not passes_checks:
            self.height += height_iteration
            if self.height > max_height:
                self.height = max_height
                break
            selfweight = self.get_beam_selfweight_per_m()
            permanent_udl_plus_swt = permanent_udl + selfweight
            ur_results = self._find_utilisation_results(
                load_duration,
                is_load_sharing,
                permanent_udl_plus_swt,
                imposed_udl,
                imposed_combination_factor,
                deflection_limit,
                is_restrained,
                permanent_load_factor,
                variable_load_factor,
                with_creep
                )

            if ur_results.get("LTB_UR") > ltb_ur:
                print("Increasing height is making lateral torsional buckling worse.")
                break

            ltb_ur = ur_results.get("LTB_UR")

            passes_checks = all(result is not None and result <= 1 for result in ur_results.values())

        results = {
            "breadth": self.breadth,
            "height": self.height,
            }
        results.update(ur_results)
        return results

    def get_auto_designed_timber_size_breadth(
            self,
            load_duration: str,
            is_load_sharing: bool,
            permanent_udl: float,
            imposed_udl: float,
            imposed_combination_factor: float,
            deflection_limit: float,
            is_restrained: bool = True,
            permanent_load_factor: float = 1.35,
            variable_load_factor: float = 1.5,
            with_creep: bool = True,
            breadth_iteration = 5,
            starting_breadth = 40,
            max_breadth = 300
            ) -> dict:
        '''Auto designs timber beam size to smallest breadth for a given height.'''
        self.breadth = starting_breadth
        selfweight = self.get_beam_selfweight_per_m()
        permanent_udl_plus_swt = permanent_udl + selfweight
        ur_results = self._find_utilisation_results(
            load_duration,
            is_load_sharing,
            permanent_udl_plus_swt,
            imposed_udl,
            imposed_combination_factor,
            deflection_limit,
            is_restrained,
            permanent_load_factor,
            variable_load_factor,
            with_creep
            )

        passes_checks = True
        for result in ur_results.values():
            if result is None:
                continue
            if result > 1:
                passes_checks = False
                break

        while not passes_checks:
            self.breadth += breadth_iteration
            if self.breadth > max_breadth:
                self.breadth = max_breadth
                break
            selfweight = self.get_beam_selfweight_per_m()
            permanent_udl_plus_swt = permanent_udl + selfweight
            ur_results = self._find_utilisation_results(
                load_duration,
                is_load_sharing,
                permanent_udl_plus_swt,
                imposed_udl,
                imposed_combination_factor,
                deflection_limit,
                is_restrained,
                permanent_load_factor,
                variable_load_factor,
                with_creep
                )

            passes_checks = all(result is not None and result <= 1 for result in ur_results.values())

        results = {
            "breadth": self.breadth,
            "height": self.height,
            }
        results.update(ur_results)
        return results
