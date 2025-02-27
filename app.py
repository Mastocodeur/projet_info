import os
import streamlit as st
from pymongo import MongoClient
from passlib.context import CryptContext
from PIL import Image
import io
# ─────────────────────────────────────────────────────────
# 1) CONNEXION À MONGODB
# ─────────────────────────────────────────────────────────

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_URI = f"mongodb+srv://loqmenanani:LHiBK757spzhBrWM@instalitre.3cjul.mongodb.net/"
client = MongoClient(MONGO_URI)


# Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)

db = client["instalitre"]  # Nom de la base de données
users_col = db["users"]  # Collection pour les utilisateurs
posts_col = db["posts"]  # Collection pour les publications

# print usernames
for user in users_col.find():
    print(user["username"])


try:
    client.server_info()  # Vérifie la connexion
    print("Connexion réussie ✅")

except Exception as e:
    print("Erreur de connexion ❌  ", e)


# Contexte de hachage pour les mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────────────────
# 2) FONCTIONS UTILITAIRES
# ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Retourne le mot de passe haché."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie qu'un mot de passe correspond à un hachage."""
    return pwd_context.verify(plain_password, hashed_password)


def get_user(username: str):
    """Recherche un utilisateur par son nom."""
    return users_col.find_one({"username": username})


def register_user(username: str, password: str):
    """Inscrit un nouvel utilisateur avec un mot de passe haché."""
    # Vérifier si l'utilisateur existe déjà
    if get_user(username):
        return False, "Nom d'utilisateur déjà pris."
    # Créer l'utilisateur
    new_user = {
        "username": username,
        "password": hash_password(password)
    }
    users_col.insert_one(new_user)
    return True, "Inscription réussie."


def login_user(username: str, password: str):
    """Tente une connexion et retourne (statut, message)."""
    user = get_user(username)
    if not user:
        return False, "Utilisateur introuvable."
    if verify_password(password, user["password"]):
        return True, "Connexion réussie."
    else:
        return False, "Mot de passe incorrect."


def add_post(user_id, image_pil, caption: str, is_private: bool):
    """Ajoute une publication dans la base avec un champ 'is_private'."""
    # Convertir l'image en binaire
    image_bytes = io.BytesIO()
    image_pil.save(image_bytes, format="PNG")
    image_binary = image_bytes.getvalue()

    # Insérer le document
    posts_col.insert_one({
        "user_id": user_id,
        "image": image_binary,
        "caption": caption,
        "is_private": is_private  # Nouveau champ
    })


def load_posts(user_id):
    """Retourne la liste des posts d'un utilisateur."""
    user_posts = posts_col.find({"user_id": user_id})
    return list(user_posts)


# ─────────────────────────────────────────────────────────
# 3) PAGE PRINCIPALE STREAMLIT
# ─────────────────────────────────────────────────────────
def main():

    logo_image = Image.open("images/logo.png")  # Ajuste le chemin si nécessaire
    st.image(logo_image, width=120)

    st.title("Instalitre")

    # Initialiser la session pour stocker les infos de l’utilisateur
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["user_id"] = None  # On peut stocker l'_id de l'utilisateur

    # ─────────────────────────────────────────────────────────
    # Barre latérale : inscription ou connexion
    # ─────────────────────────────────────────────────────────
    st.sidebar.title("Authentification")

    if not st.session_state["logged_in"]:
        # Choix: Se connecter ou s'inscrire
        choice = st.sidebar.radio("Action :", ["Se connecter", "S'inscrire"])

        if choice == "S'inscrire":
            with st.sidebar.form("register_form"):
                new_username = st.text_input("Nom d'utilisateur")
                new_password = st.text_input("Mot de passe", type="password")
                register_button = st.form_submit_button("S'inscrire")

                if register_button:
                    if new_username and new_password:
                        success, msg = register_user(new_username, new_password)
                        st.sidebar.info(msg)
                    else:
                        st.sidebar.error("Veuillez remplir tous les champs.")

        else:  # "Se connecter"
            with st.sidebar.form("login_form"):
                username = st.text_input("Nom d'utilisateur")
                password = st.text_input("Mot de passe", type="password")
                login_button = st.form_submit_button("Se connecter")

                if login_button:
                    if username and password:
                        success, msg = login_user(username, password)
                        if success:
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = username
                            user = get_user(username)
                            st.session_state["user_id"] = user["_id"]
                            st.rerun()  # <-- Ajout de cette ligne pour forcer le rechargement
                        else:
                            st.sidebar.error(msg)
                    else:
                        st.sidebar.error("Veuillez remplir tous les champs.")
    else:
        st.sidebar.write(f"Connecté en tant que {st.session_state['username']}")
        if st.sidebar.button("Se déconnecter"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = None
            st.session_state["user_id"] = None
            st.rerun()

    # ─────────────────────────────────────────────────────────
    # 4) SI UTILISATEUR CONNECTÉ : AJOUT & AFFICHAGE DE POSTS
    # ─────────────────────────────────────────────────────────
    if st.session_state["logged_in"]:
        st.subheader("Ajouter une publication")

        with st.form("post_form"):
            uploaded_image = st.file_uploader("Choisissez une image", type=["jpg", "jpeg", "png"])
            caption = st.text_input("Légende", placeholder="Description de la photo...")
            is_private = st.checkbox("Publier en privé")  # Nouveau toggle

            submit_post = st.form_submit_button("Publier")

            if submit_post:
                if uploaded_image and caption:
                    image_pil = Image.open(uploaded_image)
                    add_post(st.session_state["user_id"], image_pil, caption, is_private)
                    st.success("Publication ajoutée avec succès !")
                else:
                    st.error("Image et légende obligatoires.")

        st.subheader("Vos publications")
        user_posts = load_posts(st.session_state["user_id"])
        if user_posts:
            for post in reversed(user_posts):
                image = Image.open(io.BytesIO(post["image"]))
                st.image(image, use_container_width=True)

                # Affichage du statut actuel
                privacy_status = "Privé 🔒" if post.get("is_private") else "Public 🌍"
                st.caption(f"{post['caption']} • {privacy_status}")

                # Bouton de changement de visibilité
                current_privacy = post.get("is_private", False)
                new_privacy = not current_privacy
                button_label = "Rendre Public 🌍" if current_privacy else "Rendre Privé 🔒"

                if st.button(button_label, key=f"privacy_{post['_id']}"):
                    posts_col.update_one(
                        {"_id": post["_id"]},
                        {"$set": {"is_private": new_privacy}}
                    )
                    st.success("Visibilité modifiée avec succès !")
                    st.rerun()  # Rechargement immédiat de la page

                st.markdown("---")
        else:
            st.write("Aucune publication pour le moment.")

        # ─────────────────────────────────────────────────────────
        # 5) AFFICHAGE DES PUBLICATIONS DE TOUS LES UTILISATEURS (SAUF UTILISATEUR CONNECTÉ)
        # ─────────────────────────────────────────────────────────
        st.subheader("Publications des autres utilisateurs")

        # Exclure les publications de l'utilisateur connecté
        # Exclure les publications de l'utilisateur connecté ET filtrer celles qui ne sont pas privées
        all_posts = posts_col.find({
            "user_id": {"$ne": st.session_state["user_id"]},
            "is_private": False
        })

        if all_posts:
            for post in reversed(list(all_posts)):  # Trier par ordre d'insertion
                image = Image.open(io.BytesIO(post["image"]))
                st.image(image, use_container_width=True)

                # Récupérer l'utilisateur ayant posté
                user = users_col.find_one({"_id": post["user_id"]})
                username = user["username"] if user else "Utilisateur inconnu"

                st.caption(f"**{username}** : {post['caption']}")
                st.markdown("---")
        else:
            st.write("Aucune publication disponible pour le moment.")


if __name__ == "__main__":
    main()
