from myna.core.app.base import MynaApp


class Bnpy(MynaApp):
    def __init__(
        self,
        sim_type,
    ):
        super().__init__("bnpy")
        self.simulation_type = sim_type

        self.parser.add_argument(
            "--model",
            default=None,
            type=str,
            help="path to an existing model to use",
        )
        self.parser.add_argument(
            "--no-training",
            dest="train_model",
            action="store_false",
            help="flag to use pre-trained model",
        )
