using System.IO;
using OpenDreamRuntime.Objects.Types;

namespace OpenDreamRuntime;

public sealed partial class DreamManager {
    // Opt-in local host control. A packaged single-player session must save before
    // its server exits; the original game's continuously running server autosaves.
    // This calls the original procedure and does not change its serialization.
    private readonly string? _localSaveRequest = Environment.GetEnvironmentVariable("DM_LOCAL_SAVE_REQUEST");

    private void ProcessLocalSaveRequest() {
        if (string.IsNullOrEmpty(_localSaveRequest) || !File.Exists(_localSaveRequest)) return;
        var token = File.ReadAllText(_localSaveRequest);
        File.Delete(_localSaveRequest);
        try {
            var previousError = LastDMException;
            if (!TryGetGlobalProc("SaveUnits", out var save))
                throw new InvalidOperationException("The local world has no SaveUnits procedure");
            save.Spawn(null, new()).Dispose();
            if (!ReferenceEquals(previousError, LastDMException))
                throw new InvalidOperationException("The game's SaveUnits procedure reported an error", LastDMException);
            DreamObjectSavefile.FlushAllUpdates();
            File.WriteAllText(_localSaveRequest + ".ack", token);
            _sawmill.Info("Local host saved units before shutdown");
        } catch (Exception error) {
            File.WriteAllText(_localSaveRequest + ".error", error.ToString());
            _sawmill.Error("Local host save failed: " + error.Message);
        }
    }
}
