import subprocess

def run(cmd):
    print(f"Eseguo: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def main():
    run("git add .")
    run('git commit -m "Commit automatico dei file modificati"')
    run("git push")

if __name__ == "__main__":
    main()