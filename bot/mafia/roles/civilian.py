from mafia.roles.base import Role


class Civilian(Role):
    role = "Мирный житель"
    role_id = "civilian"
    photo = "https://cdn.culture.ru/c/820179.jpg"
    purpose = "Тебе нужно вычислить мафию на голосовании."
    payment_for_night_spent = 12
    there_may_be_several = True
