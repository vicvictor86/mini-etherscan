import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mini_etherscan_general.log", encoding="utf-8"),
    ],
)

logger_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("mini_etherscan")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("mini_etherscan.log", encoding="utf-8")
handler.setFormatter(logger_formatter)
logger.addHandler(handler)

error_logger = logging.getLogger("error_mini_etherscan")
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler("error_mini_etherscan.log", encoding="utf-8")
error_handler.setFormatter(logger_formatter)
error_logger.addHandler(error_handler)
