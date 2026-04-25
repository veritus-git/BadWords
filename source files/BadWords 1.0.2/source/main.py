#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: main.py
ROLE: Manager / Entry Point
DESCRIPTION:
Main execution file. Checks dependencies, imports configuration,
initializes the OS layer (osdoc), Resolve API, Engine, and starts the GUI.
Connects all components into a working application.
"""

import sys
import traceback
import tkinter as tk
from tkinter import messagebox
import threading
import queue

# Application module imports
import osdoc
import api
import engine
import gui

def init_system_thread(os_doc, result_queue):
    """
    Function to run in a separate thread.
    Heavy initialization (Resolve API, Engine) happens here.
    """
    try:
        # 1. Initialize API (Resolve Logic Layer) - Can be slow
        resolve = api.ResolveHandler(os_doc)

        # 2. Initialize Engine (Processing Logic Layer) - Checks FFmpeg/Whisper
        audio_engine = engine.AudioEngine(os_doc, resolve)
        
        # Put results in queue
        result_queue.put((resolve, audio_engine))
    except Exception as e:
        result_queue.put(e)

def main():
    # Variable for OSDoctor outside the try block to allow logging if init fails
    os_doc = None
    splash = None

    try:
        # 1. Initialize OSDoctor (System Layer) - Usually fast
        os_doc = osdoc.OSDoctor()
        osdoc.log_info("=== Starting BadWords ===")

        # 2. Create main Tkinter window immediately (but hide it)
        root = tk.Tk()
        root.withdraw() # Hide root initially

        # 3. Show Splash Screen immediately
        splash = gui.SplashScreen(root)
        
        # Force UI update to show splash before heavy loading starts
        root.update()

        # 4. Start Heavy Initialization in a separate Thread
        init_queue = queue.Queue()
        loading_thread = threading.Thread(target=init_system_thread, args=(os_doc, init_queue))
        loading_thread.daemon = True # Kill thread if app closes
        loading_thread.start()

        # 5. Polling Loop to check if loading is done
        def check_loading_status():
            try:
                # Check if data is available (non-blocking)
                result = init_queue.get_nowait()
                
                if isinstance(result, Exception):
                    # Initialization failed inside the thread
                    raise result
                
                # Unpack success result
                resolve, audio_engine = result
                
                # 6. Initialize Main GUI (Presentation Layer)
                # GUI receives engine (to request analysis) and resolve (timeline navigation)
                app = gui.BadWordsGUI(root, audio_engine, resolve)
                
                # 7. Destroy Splash and Show Main Window (handled by gui.py now)
                # But we ensure splash is gone here
                if splash:
                    splash.destroy()
                
                # Main window is deiconified inside BadWordsGUI constructor now to fix flickering
                
            except queue.Empty:
                # Still loading... check again in 100ms
                root.after(100, check_loading_status)

        # Start checking
        check_loading_status()

        # Configure behavior on window close
        def on_close():
            # Cleanup operations before exit
            if os_doc:
                os_doc.cleanup_temp()
            root.destroy()
            sys.exit(0) # Ensure process kills threads
            
        root.protocol("WM_DELETE_WINDOW", on_close)

        # 8. Start main loop
        osdoc.log_info("Initialization loop started.")
        root.mainloop()

    except Exception as e:
        # Critical error handling
        error_trace = traceback.format_exc()
        error_msg = f"CRITICAL ERROR: {e}\n{error_trace}"
        
        # Log error via osdoc (if initialized)
        if os_doc:
            osdoc.log_error(error_msg)
        else:
            print(error_msg) # Fallback to console
        
        # Attempt to show error window to the user
        try:
            # If root doesn't exist or was destroyed, create a temporary one
            if 'root' not in locals() or not root.winfo_exists():
                temp_root = tk.Tk()
                temp_root.withdraw() # Hide main window
                messagebox.showerror("Critical Application Error", 
                                     f"An unexpected error occurred:\n{e}\n\nDetails saved to log file.")
                temp_root.destroy()
            else:
                # Close splash if open
                if splash: splash.destroy()
                root.deiconify() # Ensure root is visible for message
                messagebox.showerror("Critical Application Error", 
                                     f"An unexpected error occurred:\n{e}\n\nDetails saved to log file.")
        except:
            pass # If even messagebox fails, nothing more we can do
        
        sys.exit(1)

if __name__ == "__main__":
    main()