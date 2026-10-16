// Odak Asistanı Native Launcher & Host
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;

[assembly: AssemblyTitle("Odak Asistanı")]
[assembly: AssemblyDescription("Odak Asistanı — Masaüstü Odak ve Ders Takip Sistemi")]
[assembly: AssemblyConfiguration("")]
[assembly: AssemblyCompany("Odak Asistanı")]
[assembly: AssemblyProduct("Odak Asistanı")]
[assembly: AssemblyCopyright("Copyright © 2026")]
[assembly: AssemblyTrademark("Odak Asistanı")]
[assembly: AssemblyCulture("")]
[assembly: ComVisible(false)]
[assembly: AssemblyVersion("2.0.0.0")]
[assembly: AssemblyFileVersion("2.0.0.0")]

namespace OdakAsistani
{
    static class Program
    {
        [STAThread]
        static int Main(string[] args)
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');
                string scriptPath = Path.Combine(baseDir, "main.py");
                
                string pythonw = @"C:\Users\kasim2\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe";
                if (!File.Exists(pythonw))
                {
                    // Fallback to local pythonw
                    pythonw = Path.Combine(baseDir, "pythonw.exe");
                }

                if (!File.Exists(scriptPath))
                {
                    return 1;
                }

                string argStr = "\"" + scriptPath + "\"";
                if (args != null && args.Length > 0)
                {
                    argStr += " " + string.Join(" ", args);
                }

                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = pythonw,
                    Arguments = argStr,
                    WorkingDirectory = baseDir,
                    UseShellExecute = true
                };

                using (Process proc = Process.Start(psi))
                {
                    if (proc != null)
                    {
                        proc.WaitForExit();
                        return proc.ExitCode;
                    }
                }
            }
            catch
            {
                return 1;
            }
            return 0;
        }
    }
}
