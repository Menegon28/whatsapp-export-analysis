import os
import subprocess
from txt_export import export_all_chats

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_menu():
    while True:
        print("\n=== WhatsApp Data Analysis Tool ===")
        print("1. Export all chats as TXT files")
        print("2. Show data analysis dashboard")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            export_all_chats()
            input("\nPress Enter to continue...")
        
        elif choice == "2":
            print("\nLaunching Streamlit dashboard...")
            subprocess.run(["streamlit", "run", "app.py"])
        
        elif choice == "3":
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice. Press Enter to try again...")
            input()

if __name__ == "__main__":
    main_menu()
