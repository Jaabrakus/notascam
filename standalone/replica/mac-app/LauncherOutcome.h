#import <Foundation/Foundation.h>

// Intentional SIGTERM is a normal quit. An explicit launcher error, including
// an unacknowledged final save, must still be visible and return failure.
typedef struct {
    BOOL showAlert;
    int resultCode;
} DMLaunchOutcome;

typedef struct {
    BOOL terminateNow;
    BOOL signalChild;
} DMLaunchTermination;

static inline DMLaunchTermination DMLaunchTerminationForRequest(BOOL finished, BOOL requestedQuit, BOOL taskRunning) {
    DMLaunchTermination decision;
    // A stopped task can still have its completion callback queued on the main
    // thread. Wait for that callback to record/report the final save outcome.
    decision.terminateNow = finished;
    decision.signalChild = !finished && !requestedQuit && taskRunning;
    return decision;
}

static inline DMLaunchOutcome DMLaunchOutcomeForExit(int exitCode, BOOL requestedQuit, NSString *status) {
    BOOL explicitError = [status hasPrefix:@"error:"];
    DMLaunchOutcome outcome;
    outcome.showAlert = explicitError || (!requestedQuit && exitCode != 0);
    outcome.resultCode = explicitError ? (exitCode != 0 ? exitCode : 1) : (requestedQuit ? 0 : exitCode);
    return outcome;
}
