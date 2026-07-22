from db import create_family, create_user

# Créer une famille
family_id = create_family("Famille Racine")

# Créer un superadmin global
superadmin_id = create_user(
    family_id=family_id,
    email="racine_jf@hotmail.com",
    password="12345",
    role="superadmin"
)

print("Famille ID:", family_id)
print("Superadmin ID:", superadmin_id)
