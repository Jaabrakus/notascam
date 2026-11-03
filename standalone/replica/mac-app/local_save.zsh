# Shared by both Mac launchers. A save succeeds only when the running server
# acknowledges this request's token after flushing the original game's saves.
dm_request_local_save() {
  local dm_save_request="$1"
  local dm_save_attempts="${2:-20}"
  local dm_save_token dm_save_attempt
  [[ "$dm_save_attempts" == <1-> ]] || return 1
  dm_save_token="$(/usr/bin/uuidgen)" || return 1
  [[ -n "$dm_save_token" ]] || return 1
  # Another diagnostic or an earlier save can leave an acknowledgment behind.
  # Clear old results, then still compare tokens in case a late result arrives.
  rm -f "$dm_save_request.ack" "$dm_save_request.error" || return 1
  print -r -- "$dm_save_token" > "$dm_save_request.pending.$$" || return 1
  if ! mv "$dm_save_request.pending.$$" "$dm_save_request"; then
    rm -f "$dm_save_request.pending.$$"
    return 1
  fi
  for (( dm_save_attempt=0; dm_save_attempt < dm_save_attempts; dm_save_attempt++ )); do
    if [[ -f "$dm_save_request.ack" && "$(cat "$dm_save_request.ack")" == "$dm_save_token" ]]; then
      return 0
    fi
    [[ -f "$dm_save_request.error" ]] && return 1
    sleep 1
  done
  [[ -f "$dm_save_request.ack" && "$(cat "$dm_save_request.ack")" == "$dm_save_token" ]]
}
