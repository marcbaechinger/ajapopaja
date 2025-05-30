if exists("g:loaded_ajapopaja")
   finish
endif
let g:loaded_ajapopaja = 1

python3 << EOF
# Imports Python modules to be used by the plugin.
import os
import sys
import threading

def AjaPopAjaSafeImport(module_names):
  for module_name in module_names:
    try:
        __import__(module_name)
    except ImportError:
        print(f"Warning: can't import {module_name}")
        return False
  return True

def AjaPopAjaAppendToSysPath(paths: list[str]):
  for path in paths:
    evaled_path = vim.eval(f"expand('{path}')")
    sys.path.append(evaled_path)

AjaPopAjaAppendToSysPath(
  [
    '~/.vim/bundle/ajapopaja/autoload/', 
    '~/monolit/code/ajapopaja/.venv/lib/python3.13/site-packages',  
  ]
)

ajaPopAja_user_home = vim.eval("expand('~/.ajapopaja')")
ajaPopAjaHasTutor = False
api_key = None
ajaPopAjaRequiredImports = ["google.genai", "ajapopaja"]
if AjaPopAjaSafeImport(ajaPopAjaRequiredImports):
  from ajapopaja import AjaPopAja
  from api_key import get_api_key
  api_key = get_api_key()
  ajaPopAjaHasTutor = api_key is not None


ajaPopAjaSystemInstruction = """You are an expert, highly efficient VIM plugin AI. Your primary goal is to empower the user to build and modify software projects and websites directly within their Vim environment in a directoy of the file system that is under Git source control.

## Your persona
You are:
- **Action-Oriented:** Focus on providing practical, executable solutions.
- **Precise and Concise:** Deliver information clearly and without unnecessary verbosity.
- **Context-Aware:** Understand Vim-specific operations, file system structures, and Git workflows.
- **Problem-Solver:** Directly address the user's coding and development challenges.
- **Safety-Conscious:** Offer clear guidance on committing or reverting changes when appropriate.
- **Instructive:** Explain your suggested actions and their purpose.

You should always:
- Prioritize generating commands and explanations that directly contribute to the user's stated task.
- Be proactive in suggesting logical next steps to guide the development process.
- Act as a seamless extension of the user's Vim workflow.

## Output Format Rules
Your response must be structured as one or more distinct "Steps". Each Step should follow this exact Markdown format starting below unitl and with out the line starting with END_OF_TEMPLATE:


# Step sequence [X]: [Brief, Action-Oriented Title]
Goal: [A concise, high-level statement of what this step aims to achieve.]

## Executable script of this step

[Executable BASH script for this step. The purpose of the script is to create, edit or delete resources to complete the step. 
- The section is fenced by a markup code block for the 'bash' language
- The first line of the script is the hash bang followed by a blank line and a line in the format `# step: 42` where 42 is the step sequence.
- Edits of text files or creation of new text files are implemented with `cat` or similar cli tools. Below two shortened examples for an HTML or Python source file. These are just examples, the reources can be of any type of source code and text files that you find useful for the project.

cat > www/index.html <<HTML
#!/usr/bin/env HTML
<html><body></body></html>
HTML

cat > src/tools/serve.py <<PY
#!/usr/bin/env python3

import http.server

]
- Important: After the execution of the script, the intended modifications is completed and the project is properly working as intended. Ne project is never left in a broken state.

##Explanation

[A detailed explanation of how the provided code/commands achieve the goal, why this approach is taken, and any relevant context or considerations. This should be clear and informative, justifying the suggested actions.]

## User commands

[Executable VIM commands or vimscript with an explanation on how to use them from within Vim. These commands help the user for instance to navigate to the changes applied by this step. The commands generally facilitate and encourage the user to inspect, asses, validate and test the new state of the repo that resulted from this step. If useful you can generate and present auxiliary scripts in vimscript, BASH or Python that help achieving these goals. Be creative and present som intrersting and efficient ways to surface import concepts or designs of the evolving project. These are the script types that in the output are fenced in a corresponding markdown script section:
- 'vimscript': For Vim's native Ex commands, normal mode commands (prefixed with 'normal! '), or VimL function calls. Can call unix cli tools or Python code.
- 'bash': For standard shell commands, Git commands, system utilities, or scripts.
- 'python': For Python code intended to be executed within Vim's embedded Python interpreter (e.g., using `:py3`) or stored in a file and executed from the shell executed by ':!python %'. This is useful for more complex logic, file I/O within the plugin context, or interacting with Python libraries. The user can then colect these tools in the repo.]

## Acceptance Criteria

[Actionable hint(s) for the user to verify the success and completeness of this step. This can involve running tests, checking file contents, verifying command output, or observing Vim's state. Some examples below for inspiration. Be creative.]
- Example (Bash): Run: python -m unittest tests/my_module_test.py
- Example (Vimscript): Check: Open 'output.log' and ensure it contains "SUCCESS".
- Example (File Content): Verify: The file 'src/app.py' now contains the line 'app.route("/")'.
- Example (Interactive): Observe: Vim's command line should display "File created successfully."
- Important: Provide specific, clear and actional instructions and make references to the 'User commands' from the previous section above

## Git actions

[Choose from the following options, strictly adhering to the format below. Place the git cammands in a fenced bash code section. Add the step sequence to the commit message.]
- `git init && git add . && git commit -m "Initial commit."`: If this is the first step of a task without a current git status report.
- `git commit -m "Descriptive commit message for this step in imperative form"`: If changes are significant and ready to be committed after this step.
- `git add <paths> && git commit -m "Descriptive commit message for this step in imperative form"`: If specific files should be added and committed.
- `git reset --hard HEAD`: If this step is part of a series where the user might want to easily undo the last action. Explain what it measn if you suggest so.
- No Git action for this step.: If no commit or explicit undo action is immediately relevant.
- Important: The commit message describes the change of the entire step and not the change compared to the script of the last conversation turn.

## Next Steps/Iteration

[
- Suggest what the user should do immediately after this step (e.g., "Run tests.", "Review the generated file.").
- If the overall task is not complete, clearly state the next logical step Gemini will address upon confirmation.
- If the task is complete, explicitly state "Task complete." and provide a summary or final recommendations.
- Ask a clarifying question if more input is needed to proceed with the next step.
]

END_OF_TEMPLATE

Important Notes for Generation:

- Always provide at least one complete Step.
- Vim commands calling Vimscripts are prefered specificatlly for smaller and simpler changes. They can call bash and Pythong scripts in functions or here-documents if its a more complicated logic.
- Break down larger tasks into smaller, manageable Steps. If a task requires multiple steps, only provide the current step's full details. The "Next Steps/Iteration" section should then indicate that further steps will be provided upon user confirmation or explicit request.
- Ensure all code blocks are properly fenced with the correct language identifier (vimscript,bash, ```python).
- Each step results in a working state of the artefacts after the proposed code blocks have been executed.
- Make sure explanations are concise but comprehensive enough to understand the purpose of the code.
- Crucially, always provide clear and actionable Acceptance Criteria for each step."""

if api_key is None:
  print("please provide an API key as env variable GOOGLE_API_KEY to use the Gemini API")
elif not ajaPopAjaHasTutor:
  print("some required imports not available out of ", ajaPopAjaRequiredImports)
else:
  workspace_parent = os.path.join(ajaPopAja_user_home, "workspaces")
  logfile_dir = os.path.join(ajaPopAja_user_home, "trace")
  tutor = AjaPopAja(api_key, ajaPopAjaSystemInstruction, workspace_parent, logfile_dir)


def AjaPopAjaSetNavigationInfo(index):
  size = len(tutor.history.entries)
  navigationInfo = f"({index + 1}/{size})"
  vim.command(f"let g:AjaPopAjaNavigationInfo = '{navigationInfo}'")
  return navigationInfo


def AjaPopAjaPromptCallback():
  index, historyItem = tutor.get_last()
  AjaPopAjaSetNavigationInfo(index)
  vim.command("call AjaPopAjaFetchResponse()");


def AjaPopAjaPromptBlocking(prompt):
  tutor.prompt(prompt.decode('utf-8'))
  AjaPopAjaPromptCallback()


def AjaPopAjaPromptAsync():
  prompt = vim.vars['AjaPopAjaValue']
  thread = threading.Thread(
      target=AjaPopAjaPromptBlocking,
      args = (prompt,)
  )
  thread.daemon = True 
  thread.start()
  return ""


def AjaPopAjaSelectAndReturnPreviousResponse():
  prev = tutor.select_previous()
  if prev is None:
    return ""
  size = len(tutor.history.entries)
  navigationInfo = AjaPopAjaSetNavigationInfo(prev[0])
  header = f"# -- {navigationInfo} in history --\n"
  historyItem = prev[1]
  return header + historyItem.response


def AjaPopAjaSelectAndReturnNextResponse():
  nextItem = tutor.select_next()
  if nextItem is None:
    return "" 
  size = len(tutor.history.entries)
  index = nextItem[0]
  navigationInfo = AjaPopAjaSetNavigationInfo(index)
  header = f"# -- {navigationInfo} in history --\n" if index < size else ""
  historyItem = nextItem[1]
  return header + historyItem.response


def AjaPopAjaGetTotalTokenStats():
  if not ajaPopAjaHasTutor:
    return "0/0"
  return str(tutor.get_prompt_token_count()) + "/" + str(tutor.get_candidates_token_count())


def AjaPopAjaGetSelectedTokenStats():
  if not ajaPopAjaHasTutor:
    return "-/-"
  _ , historyEvent = tutor.get_selected()
  if historyEvent is not None:
    return str(historyEvent.prompt_token_count) + "/" + str(historyEvent.candidates_token_count)
  else:
    return "-/-"


EOF

let s:promptBufferName = expand('~') . '/.ajapopaja/prompt.ajapopaja'
let s:responseBufferName = expand('~') . '/.ajapopaja/response.md'
let s:window_counter = 1
let s:readOnlyMarker = "^>"
let s:statusDefault = "Enter prompt."
let s:statusEditing = "Leave normal mode."
let s:statusEdited = "Press ? to prompt."
let s:statusThinking = "Sent prompt. Thinking..."
let s:statusResponded = "Response written."
let s:isAiThinking = 0

let g:AjaPopAjaStatus = "Not yet started"
let g:AjaPopAjaTotalTokenStats = "[-/-]"
let g:AjaPopAjaSelectedTokenStats = "[-/-]"
let g:AjaPopAjaNavigationInfo = ""

function! s:setAjaPopAjaStatus(status)
  let g:AjaPopAjaStatus = a:status
endfunction

function! s:getTotalTokenStats()
  let g:AjaPopAjaTotalTokenStats = py3eval('AjaPopAjaGetTotalTokenStats()')
endfunction

function! s:getSelectedTokenStats()
  let g:AjaPopAjaSelectedTokenStats = py3eval('AjaPopAjaGetSelectedTokenStats()')
endfunction

call s:getTotalTokenStats()
call s:getSelectedTokenStats()

function! s:appendToPrompt(text, markAsReadOnly)
  let winid = s:getPromptWinId()
  if winid != -1
    let lastLine = line('$', winid)
    let bufname = bufname(s:promptBufferNr)
    call appendbufline(bufname, lastLine, a:text) 
    let insertion_end = line('$', winid)
    if a:markAsReadOnly
      call s:markLinesReadOnly(lastLine, lastLine + 1, bufname)
    endif
  endif
endfunction

function! s:askTutor(prompt)
  let g:AjaPopAjaValue = trim(a:prompt)
  let nothing = py3eval('AjaPopAjaPromptAsync()')
  call s:setAjaPopAjaStatus(s:statusThinking)
  let s:isAiThinking = 1
endfunction

function! AjaPopAjaFetchResponse()
  let s:isAiThinking = 0
  let code = py3eval('tutor.get_last_response()')
  call s:renderResponse(code) 
  call s:getSelectedTokenStats()
  call s:setAjaPopAjaStatus(s:statusResponded . " ->")
  call s:getTotalTokenStats()
  redraw!
endfunction

function! s:renderResponse(code)
  let winid = s:getResponseWinId()
  if winid != -1
    let lastLine = line('$', winid)
    let bufname = bufname(s:responseBufferNr)
    call deletebufline(bufname, 1, lastLine)
    call appendbufline(bufname, 1, split(a:code, "\n", 1)) 
  endif
endfunction

function! s:markLinesReadOnly(start_line, end_line, bufname)
  let lnum = a:start_line
  while lnum <= a:end_line
    let lines = getbufline(a:bufname, lnum, lnum + 1)
    if !empty(lines)
      let line_text = lines[0]
      if line_text !~# s:readOnlyMarker
        call setbufline(a:bufname, lnum, '> ' . line_text)
      endif
    endif
    let lnum = lnum + 1
  endwhile
endfunction

function! s:togglePrompt()
  call s:ensureDirectoryExists(expand('~') . '/.ajapopaja')
  if !exists("s:promptBufferNr")
    let s:windowId = s:window_counter
    let s:promptBufferNr = 0
    let s:responseBufferNr = 0
    let s:window_counter = s:window_counter + 1
    call s:setAjaPopAjaStatus(s:statusDefault)
  endif
  if s:promptBufferNr && bufexists(s:promptBufferName)
    execute 'bd!' s:promptBufferNr
    execute 'bd!' s:responseBufferNr
    let s:promptBufferNr = 0
    let s:responseBufferNr = 0
  else
    let old_splitright = &splitright
    set splitright
    execute "vsplit" s:responseBufferName
    setlocal bufhidden=hide
    setlocal buftype=nofile
    setlocal nobuflisted
    setlocal noswapfile
    execute "split" s:promptBufferName
    resize 16 
    vert resize 120
    setlocal bufhidden=hide
    setlocal nobuflisted
    setlocal noswapfile
    let s:promptBufferNr = bufnr(s:promptBufferName)
    let s:responseBufferNr = bufnr(s:responseBufferName)
    let &splitright = old_splitright
    silent! execute '$'
    normal! ^
  endif
endfunction

function! s:how(query)
    if trim(a:query) ==# ""
      call s:echoWarning("Empty prompt")
      call s:setAjaPopAjaStatus(s:statusDefault)
      return
    endif
    let g:AjaPopAjaStatus = "Asking tutor..."
    call s:askTutor(a:query)
endfunction

function! s:prompt(bufname)
  let winId = s:getPromptWinId()
  let prompt = ""
  if winId != -1
    let lastLineNr = line('$', winId)
    let lines = getbufline(a:bufname, 1, lastLineNr)
    let filteredLines = filter(lines, 'v:val !~# "^>"')
    if len(filteredLines) < 1
      echomsg "Empty prompt"
      call s:setAjaPopAjaStatus(s:statusDefault)
      return
    endif
    let prompt = join(filteredLines, "\n")
    call s:markLinesReadOnly(0, lastLineNr, s:promptBufferName)
    let g:AjaPopAjaStatus = "Asking tutor..."
    write
    call s:askTutor(prompt)
  endif
endfunction

function! s:displayPrevious()
  let response = py3eval('AjaPopAjaSelectAndReturnPreviousResponse()')
  if response ==# ''
    echo "Already at the end of the history"
  else
    call s:renderResponse(response)
    call s:getSelectedTokenStats()
  endif
endfunction

function! s:displayNext()
  let response = py3eval('AjaPopAjaSelectAndReturnNextResponse()')
  if response ==# ''
    echo "Already at the actual output"
  else
    call s:renderResponse(response)
    call s:getSelectedTokenStats()
  endif
endfunction

function! s:popupPrompt()
  let lNum = line('.')
  let prompt = trim(py3eval('tutor.get_selected_prompt()'))
  call setreg("*", prompt)
  let options = #{line: 0, col: 0, title:' Last prompt', time:10000, maxwidth:72, close:'click'}
  call popup_notification(split(prompt, "\n", 1), options)
endfunction

function s:hasPrompt()
  if s:promptBufferNr
    for line in getbufline(s:promptBufferName, 1, '$')
      if line !~# '^>'
        return 1
      endif
    endfor
  endif
  return 0
endfunction

function! s:setAjaPopAjaStatusAfterEditing()
  if s:isAiThinking
    return
  endif
  if s:hasPrompt() == 1
    call s:setAjaPopAjaStatus(s:statusEdited)
  else
    call s:setAjaPopAjaStatus(s:statusDefault)
  endif
endfunction

" UI functions

function! s:getPromptWinId()
  if !s:promptBufferNr
    return -1
  endif
  let winids = win_findbuf(s:promptBufferNr)
  if !empty(winids)
    return winids[0]
  endif
  return -1
endfunction

function! s:getResponseWinId()
  if !s:responseBufferNr
    return -1
  endif
  let winids = win_findbuf(s:responseBufferNr)
  if !empty(winids)
    return winids[0]
  endif
  return -1
endfunction

" utility functions

function! s:ensureDirectoryExists(directory_path)
  if !isdirectory(a:directory_path)
    silent! call mkdir(a:directory_path, "p")
    if !isdirectory(a:directory_path)
      return 0 
    endif
  endif
  return 1 
endfunction

function! s:urlEncode(str)
  let encoded = substitute(a:str, '[^A-Za-z0-9_.-~]', '\=%02X', 'g')
  return encoded
endfunction

function! s:echoWarning(message)
  call s:echoColoredMessage("WarningMsg", a:message)
endfunction
 
function! s:echoError(message)
  call s:echoColoredMessage("ErrorMsg", a:message)
endfunction
 
function! s:echoColoredMessage(color, message)
  " Use hl groups WarningMsg, ErrorMsg, InfoMsg. See `:h echohl` for details
  execute 'echohl ' . a:color
  echomsg a:message
  echohl None
endfunction

function! s:executeSelectedStep()
  call py3eval('tutor.execute_selected_code_section()')
endfunction

function! s:presentSelectedUserActions()
endfunction

" define auto commands

if !exists(":AjaPopAjaTogglePrompt")
  command -nargs=0  AjaPopAjaTogglePrompt :call s:togglePrompt()
  command -nargs=0  AjaPopAjaPrompt :call s:prompt(s:promptBufferName)
  command -nargs=1  AjaPopAja :call s:how(<args>)
  command -nargs=0  AjaPopAjaSelectPrevious :call s:displayPrevious()
  command -nargs=0  AjaPopAjaSelectNext :call s:displayNext()
  command -nargs=0  AjaPopAjaPopupPrompt :call s:popupPrompt()
  command -nargs=0  AjaPopAjaExecuteSelectedStep :call s:executeSelectedStep()
  command -nargs=0  AjaPopAjaPresentSelectedUserActions :call s:presentSelectedUserActions()
endif

augroup AjaPopAjaAutoCommands
  au! BufRead,BufNewFile *.ajapopaja set filetype=ajapopaja
  au! BufEnter,BufLeave *.ajapopaja :call s:setAjaPopAjaStatus(s:statusDefault)
  au! InsertEnter *.ajapopaja :call s:setAjaPopAjaStatus(s:statusEditing)
  au! InsertLeave,TextChanged *.ajapopaja :call s:setAjaPopAjaStatusAfterEditing()
augroup END

augroup AjaPopAjaMappings
  autocmd!
  autocmd FileType ajapopaja nnoremap <buffer> <S-F9> :AjaPopAjaPopupPrompt<CR>
  autocmd FileType ajapopaja nnoremap <buffer> ? :AjaPopAjaPrompt<CR>
  autocmd FileType ajapopaja nnoremap <buffer> <S-Left> :AjaPopAjaSelectPrevious<CR>
  autocmd FileType ajapopaja nnoremap <buffer> <S-Right> :AjaPopAjaSelectNext<CR>
  autocmd FileType ajapopaja nnoremap <buffer> C :%d _<CR>
  autocmd FileType markdown nnoremap <buffer> <F9> :AjaPopAjaExecuteSelectedStep<CR>
augroup END

nnoremap <silent> <S-F6> :AjaPopAjaTogglePrompt<CR> 

