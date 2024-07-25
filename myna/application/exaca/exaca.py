from myna.application.base import MynaApp


class ExaCA(MynaApp):

    def __init__(self, argv):
        super().__init__("ExaCA")

        # Setup ExaCA specific inputs
        self.parser.add_argument(
            "--cell-size", type=float, help="(float) ExaCA cell size in microns"
        )
        self.parser.add_argument(
            "--nd",
            type=float,
            default=1,
            help="(float) Multiplier for nucleation density, 10^(12) * nd)",
        )
        self.parser.add_argument(
            "--mu",
            type=float,
            default=10,
            help="(float) Critical undercooling mean temperature "
            + "for nucleation, in Kelvin",
        )
        self.parser.add_argument(
            "--std",
            type=float,
            default=2,
            help="(float) Standard deviation for undercooling, in Kelvin",
        )
        self.parser.add_argument(
            "--sub-size",
            type=float,
            default=12.5,
            help="(float) Grain size of substrate, in microns",
        )

        self.args = self.parser.parse_args(argv)

        super().check_exe(
            "exaca",
            "microstructure_region",
            "ExaCA",
            "build",
            "install",
            "bin",
            "ExaCA",
        )

        super().set_template_path("exaca", "microstructure_region")