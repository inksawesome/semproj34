import random

class ChallengeGenerator:
    def __init__(self):
        self.challenges = ["TURN_LEFT", "TURN_RIGHT", "BLINK", "SMILE", "LOOK_UP"]
    
    def get_random_challenge(self) -> str:
        return random.choice(self.challenges)
