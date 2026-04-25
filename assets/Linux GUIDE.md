#### 1\) Download

Download the .zip installation pack from releases or shortcuts on the top of README file and extract it into a folder

#### 2\) Run the Installer

Open the folder in your terminal and run the setup script:

**Make it executable**  
chmod \+x setup_file_name.sh

**Run the installer**  
./setup_file_name.sh

**The script will:**

* Ask for sudo to install minimal dependencies (ffmpeg, python3-tk, pipx).  
* Install OpenAI Whisper in a safe, isolated environment.  
* Configure the script in DaVinci Resolve.

### 3\) Launch in DaVinci Resolve

1. Open DaVinci Resolve.  
2. Open your Project and Timeline.  
3. Go to Workspace → Scripts → BadWords  
4. Enjoy easier editing\!

### 4\) Uninstallation

To remove the program, open a terminal in the folder where the setup script is located and run it again:

**Run the installer**  
./setup_file_name.sh

**Then:**

1. From the main menu, select option **4** (Uninstall).  
2. When prompted, type `yes` and press Enter to confirm the complete removal of all files.