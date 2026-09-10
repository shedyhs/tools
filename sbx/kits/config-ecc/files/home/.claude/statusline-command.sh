#!/usr/bin/env bash
# Claude Code status line — robbyrussell Oh My Zsh theme style

export LC_NUMERIC=C

# ANSI color codes (standard, not bold — status line is rendered dimmed)
green='\033[32m'
cyan='\033[36m'
blue='\033[34m'
red='\033[31m'
yellow='\033[33m'
magenta='\033[35m'
reset='\033[0m'

# One jq pass for every field we need. Fields are joined with US (0x1f) rather
# than a tab: tab counts as IFS whitespace, so bash would collapse runs of them
# and shift every field left whenever a value is absent. `join` renders null as
# an empty field, which matches the `// empty` guards this used to do.
IFS=$'\x1f' read -r cwd model_name ctx_used ctx_tokens five_h_pct five_h_resets seven_d_pct seven_d_resets \
  < <(jq -r '[
        (.workspace.current_dir // .cwd // ""),
        .model.display_name,
        .context_window.used_percentage,
        .context_window.total_input_tokens,
        .rate_limits.five_hour.used_percentage,
        .rate_limits.five_hour.resets_at,
        .rate_limits.seven_day.used_percentage,
        .rate_limits.seven_day.resets_at
      ] | join("\u001f")')

dir_basename=${cwd##*/}
[ -z "$dir_basename" ] && dir_basename=$cwd

# Read the clock once, from the shell itself, instead of forking `date` per countdown
now=${EPOCHSECONDS:-$(date +%s)}

# Helper: convert a Unix epoch to a compact countdown string ("2h30m", "4d12h", "45m").
# Assigns to the variable named by $2 so callers don't pay for a command substitution.
fmt_countdown() {
  local target=$1 out=$2 diff d h m
  diff=$(( target - now ))
  if [ "$diff" -le 0 ]; then
    printf -v "$out" "0m"
    return
  fi
  d=$(( diff / 86400 ))
  h=$(( (diff % 86400) / 3600 ))
  m=$(( (diff % 3600) / 60 ))
  if [ "$d" -gt 0 ]; then
    printf -v "$out" "%dd%dh" "$d" "$h"
  elif [ "$h" -gt 0 ]; then
    printf -v "$out" "%dh%02dm" "$h" "$m"
  else
    printf -v "$out" "%dm" "$m"
  fi
}

# Build git info if inside a repo. A single `status --porcelain=v2 --branch` carries
# both the branch and the dirty state, replacing the old rev-parse/diff/ls-files calls.
git_info=""
wt_info=""
if [ -n "$cwd" ]; then
  branch=""
  oid=""
  dirty=0
  while IFS= read -r line; do
    case $line in
      '# branch.oid '*)  oid=${line#'# branch.oid '} ;;
      '# branch.head '*) branch=${line#'# branch.head '} ;;
      '#'*) ;;
      # The first worktree entry is enough to know we're dirty (untracked files
      # count as dirty, matching robbyrussell) — stop reading and let git go.
      ?*) dirty=1; break ;;
    esac
  done < <(git -C "$cwd" --no-optional-locks status --porcelain=v2 --branch 2>/dev/null)

  # Detached HEAD reports "(detached)" as the branch name — show the short oid instead
  if [ "$branch" = "(detached)" ]; then
    branch=${oid:0:7}
    [ "$oid" = "(initial)" ] && branch=""
  fi

  if [ -n "$branch" ]; then
    if [ "$dirty" -eq 0 ]; then
      printf -v git_info " ${blue}git:(${red}%s${blue})${reset}" "$branch"
    else
      printf -v git_info " ${blue}git:(${red}%s${blue}) ${yellow}✗${reset}" "$branch"
    fi
  fi

  # Worktree info — one rev-parse yields both dirs. A linked worktree keeps its
  # git dir at <common>/worktrees/<name>, so the two paths differ there and
  # match in the main worktree. --path-format=absolute keeps the comparison
  # honest (plain rev-parse would print a bare ".git" for the main one).
  { read -r git_dir; read -r common_dir; } \
    < <(git -C "$cwd" rev-parse --path-format=absolute --git-dir --git-common-dir 2>/dev/null)

  if [ -n "$git_dir" ]; then
    if [ "$git_dir" != "$common_dir" ]; then
      printf -v wt_info " ${magenta}wt:(${red}%s${magenta})${reset}" "${git_dir##*/}"
    else
      # Main worktree: only worth naming when linked worktrees actually exist.
      # Plain glob, no fork — an unmatched pattern fails the -e test.
      linked=("$common_dir"/worktrees/*/)
      if [ -e "${linked[0]}" ]; then
        printf -v wt_info " ${magenta}wt:(${red}main${magenta}+%d)${reset}" "${#linked[@]}"
      fi
    fi
  fi
fi

# Context window usage (null before first message)
ctx_info=""
if [ -n "$ctx_used" ]; then
  if [ -n "$ctx_tokens" ] && [ "$ctx_tokens" -gt 0 ] 2>/dev/null; then
    # "47000e-3" is 47.0 to printf — divides by 1000 without forking awk
    printf -v ctx_k "%.0fk" "${ctx_tokens}e-3"
    printf -v ctx_info "  ${magenta}ctx:%s (%.0f%%)${reset}" "$ctx_k" "$ctx_used"
  else
    printf -v ctx_info "  ${magenta}ctx:%.0f%%${reset}" "$ctx_used"
  fi
fi

# 5-hour usage — percentage + countdown to reset (absent for non-subscribers or before first API response)
five_h_info=""
if [ -n "$five_h_pct" ]; then
  if [ -n "$five_h_resets" ]; then
    fmt_countdown "$five_h_resets" five_h_left
    printf -v five_h_info "  ${yellow}5h:%.0f%%·%s${reset}" "$five_h_pct" "$five_h_left"
  else
    printf -v five_h_info "  ${yellow}5h:%.0f%%${reset}" "$five_h_pct"
  fi
fi

# 7-day weekly usage — percentage + countdown to reset
seven_d_info=""
if [ -n "$seven_d_pct" ] || [ -n "$seven_d_resets" ]; then
  pct_part=""
  left_part=""
  [ -n "$seven_d_pct" ] && printf -v pct_part "%.0f%%" "$seven_d_pct"
  [ -n "$seven_d_resets" ] && fmt_countdown "$seven_d_resets" left_part
  if [ -n "$pct_part" ] && [ -n "$left_part" ]; then
    printf -v seven_d_info "  ${cyan}7d:%s·%s${reset}" "$pct_part" "$left_part"
  elif [ -n "$pct_part" ]; then
    printf -v seven_d_info "  ${cyan}7d:%s${reset}" "$pct_part"
  else
    printf -v seven_d_info "  ${cyan}7d↻%s${reset}" "$left_part"
  fi
fi

# Model display name
model_info=""
if [ -n "$model_name" ]; then
  printf -v model_info "  ${green}%s${reset}" "$model_name"
fi

printf "${green}${reset}  ${cyan}%s${reset}%s%s%s%s%s%s\n" \
  "$dir_basename" "$git_info" "$wt_info" "$ctx_info" "$five_h_info" "$seven_d_info" "$model_info"
