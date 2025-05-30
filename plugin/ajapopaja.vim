if exists("g:loaded_ajapopaja")
   finish
endif
let g:loaded_ajapopaja = 1

echomsg "ajapopaja"
python3 << EOF
# Imports Python modules to be used by the plugin.
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
    '/Users/marcbaechinger/monolit/code/ajapopaja/.venv/lib/python3.13/site-packages',  
  ]
)
ajaPopAjaHasTutor = False
api_key = None
ajaPopAjaRequiredImports = ["google.genai", "tutor"]
if AjaPopAjaSafeImport(ajaPopAjaRequiredImports):
  from tutor import VimTutor
  from api_key import get_api_key
  api_key = get_api_key()
  ajaPopAjaHasTutor = api_key is not None

ajaPopAjaSystemInstruction = (
    "You are an expert vim tutor."
    "You give clear an concise advise on how to use vim."
    "Your output are vim commands or vimscript functions that help the user programming with vim."
    "Start with the sequence of commands or the functions and then explain step by step how the user can achieve the declared goal."
    "Format your output in markdown format"
    "Line width must not exeed 80 characters."
)

if api_key is None:
  print("please provide an API key as env variable GOOGLE_API_KEY to use the Gemini API")
elif not ajaPopAjaHasTutor:
  print("some required imports not available out of ", ajaPopAjaRequiredImports)
else:
  tutor = VimTutor(api_key, ajaPopAjaSystemInstruction, vim.eval("expand('~/.ajapopaja/trace')")
)

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

" define auto commands

if !exists(":AjaPopAjaTogglePrompt")
  command -nargs=0  AjaPopAjaTogglePrompt :call s:togglePrompt()
  command -nargs=0  AjaPopAjaPrompt :call s:prompt(s:promptBufferName)
  command -nargs=1  AjaPopAja :call s:how(<args>)
  command -nargs=0  AjaPopAjaSelectPrevious :call s:displayPrevious()
  command -nargs=0  AjaPopAjaSelectNext :call s:displayNext()
  command -nargs=0  AjaPopAjaPopupPrompt :call s:popupPrompt()
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
  autocmd FileType ajapopaja nnoremap <buffer> <S-Left> :AjaPopAjaSelectPrevious<CR>
  autocmd FileType ajapopaja nnoremap <buffer> <S-Right> :AjaPopAjaSelectNext<CR>
  autocmd FileType ajapopaja nnoremap <buffer> C :%d _<CR>
augroup END

nnoremap <silent> <S-F6> :AjaPopAjaTogglePrompt<CR> 

