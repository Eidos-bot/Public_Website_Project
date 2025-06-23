import hashlib
import secrets

# This is how i imagine the password creation process will go

def create_password(to_be_hashed, salter=secrets.token_hex(10), lc=True):
    hashed_obj = hashlib.sha3_512((to_be_hashed + salter).encode())
    if lc:

        return hashed_obj.hexdigest()
    else:
        return hashed_obj.hexdigest(), salter


if __name__ == "__main__":

    hash_user_dict = {}

    while True:

        create_or_login = input("Create or Login? [y/n] ")
        print(hash_user_dict)

        if create_or_login == 'y':
            username = input("Enter new username.")
            password = input("Enter new password.")

            hash_user_dict[username]=create_password(password, lc=False)

        elif create_or_login == 'n':

            username = input("Enter username.")
            password = input("Enter password.")

            if hash_user_dict.get(username):
                x,y = hash_user_dict[username]
                if x == create_password(password, salter=y):
                    print("Successful log in.")
                else:
                    print("Wrong password.")
            else:
                print("Invalid username.")