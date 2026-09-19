import random

class ChallengeGenerator:
    def __init__(self):
        # List of supported active liveness challenges
        self.challenges = ["TURN_LEFT", "TURN_RIGHT", "BLINK", "SMILE", "LOOK_UP"]
    
    def get_random_challenge(self) -> str:
        """
        Selects a random challenge for the user to perform.
        """
        return random.choice(self.challenges)
