import structlog

log = structlog.get_logger(__name__)



def create_player_a(minVal:int, maxVal:int, max_attempts:int, player_id:str):
    log.info("create_player_a", player_a_id = str(player_id))
    return ""

def create_player_b(minVal:int, maxVal:int, max_attempts:int, player_id:str):
    log.info("create_player_b", player_b_id = str(player_id))
    return ""
