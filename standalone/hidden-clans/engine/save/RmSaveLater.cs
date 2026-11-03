using System.IO;
using System.Threading.Tasks;

namespace OpenDreamRuntime;

// Remastered (engine/save/save_patch.py; the spike hunt, 10-31): a savefile the game marks rm_later (the autosave's unit
// saves, Saves.dm) is turned into text and written off the game thread when it closes, so the tick that saves no longer
// waits for the text or the disk. Any read, exists-check, copy or delete of a file waits for those writes first, and the
// process waits for them before it exits. Each goes to "<path>.rmtmp" and then replaces the file, so a crash mid-write
// leaves the last save whole.
public static class RmSaveLater {
    private static readonly List<Task> Pending = new();
    private static bool _hooked;

    // path: where the save goes; stand_in: the fresh file the game opened in its place, removed once the save is in.
    public static void Write(Func<string> text, string path, string? standIn = null) {
        var task = Task.Run(() => {
            var tmp = path + ".rmtmp";
            File.WriteAllText(tmp, text() + "\r\n");
            File.Move(tmp, path, true);
            if (standIn != null) File.Delete(standIn);
        });
        lock (Pending) {
            Pending.Add(task);
            if (!_hooked) {
                _hooked = true;
                AppDomain.CurrentDomain.ProcessExit += (_, _) => Wait();
            }
        }
    }

    // Every write still going, finished; cheap when there are none.
    public static void Wait() {
        Task[] tasks;
        lock (Pending) {
            if (Pending.Count == 0) return;
            tasks = Pending.ToArray();
            Pending.Clear();
        }
        foreach (var task in tasks) {
            try {
                task.Wait();
            } catch (Exception e) {
                Robust.Shared.Log.Logger.GetSawmill("opendream.res").Error($"Remastered: a save written off the game thread failed: {e.InnerException ?? e}");
            }
        }
    }
}
