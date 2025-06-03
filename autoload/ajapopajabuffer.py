import os
import vim

__all__ = ["extract_and_save_fenced_code"]

# Main function, now orchestrating the helpers
def extract_and_save_fenced_code(directory, filename):
    """
    Extracts the content of a Markdown code block from the current Vim buffer
    and saves it to a specified file.

    The function identifies the code block based on the current cursor position.
    It searches upwards for an opening fence ("```") and downwards for a
    closing fence ("```"). The content between these fences (exclusive) is
    then written to the specified file.

    Args:
        directory (str): The directory where the file will be saved.
                         If it doesn't exist, it will be created.
        filename (str): The name of the file to save the content to.

    Returns:
        dict: A dictionary indicating the outcome of the operation.
              On success:
                {'status': 'success',
                 'opening_line': int,  # 1-indexed line number of opening fence
                 'closing_line': int,  # 1-indexed line number of closing fence
                 'directory': str,
                 'filename': str}
              On failure:
                {'status': 'error',
                 'message': str,  # Description of the error
                 'opening_line': int (optional), # If opening fence was found
                 'closing_line': int (optional), # If closing fence was found
                 'directory': str (optional),
                 'filename': str (optional)}
    """
    try:
        current_buffer = vim.current.buffer
        if not current_buffer:
            vim.command("echohl WarningMsg | echom 'Python: No current buffer.' | echohl None")
            return {'status': 'error', 'message': 'No current buffer'}

        fence_info = _find_fenced_block_lines(current_buffer)

        if fence_info['status'] == 'error':
            # Message already echoed by _find_fenced_block_lines
            return fence_info # Propagate error dict

        opening_line_num = fence_info['opening_line_num']
        closing_line_num = fence_info['closing_line_num']
        opening_fence_idx = fence_info['opening_fence_idx']
        closing_fence_idx = fence_info['closing_fence_idx']

        content_to_save = _extract_text_from_buffer_lines(
            current_buffer, # Pass current_buffer here as well
            opening_fence_idx,
            closing_fence_idx
        )
        
        os.makedirs(directory, exist_ok=True)
        save_result = _save_text_to_file(content_to_save, directory, filename)

        if save_result['status'] == 'error':
            return {
                'status': 'error',
                'message': save_result['message'],
                'opening_line': opening_line_num, # Keep line info for context
                'closing_line': closing_line_num,
                'directory': directory,
                'filename': filename
            }
        
        # If all steps successful
        return {
            'status': 'success',
            'opening_line': opening_line_num,
            'closing_line': closing_line_num,
            'directory': directory,
            'filename': filename
        }

    except Exception as e:
        # Catch-all for unexpected errors in the orchestration logic itself
        error_message = str(e).replace("'", "''")
        vim.command(f"echohl ErrorMsg | echom 'Python Error in extract_and_save_fenced_code orchestration: {error_message}' | echohl None")
        return {'status': 'error', 'message': f'An unexpected Python error occurred during orchestration: {str(e)}'}


# Helper function to find opening and closing fence lines
def _find_fenced_block_lines(buffer_obj):
    """
    Finds the line numbers of the opening and closing fences of a Markdown code block.

    Searches relative to the current cursor position in the provided Vim buffer object.
    It looks for an opening fence ("```") by searching upwards from the cursor
    and a closing fence ("```") by searching downwards from the opening fence.

    Args:
        buffer_obj: The Vim buffer object to search within.

    Returns:
        dict: On success:
                {'status': 'success',
                 'opening_line_num': int,  # 1-indexed line number of opening fence
                 'closing_line_num': int,  # 1-indexed line number of closing fence
                 'opening_fence_idx': int, # 0-indexed buffer line index of opening fence
                 'closing_fence_idx': int} # 0-indexed buffer line index of closing fence
              On failure, if opening fence is not found:
                {'status': 'error', 'message': 'Opening fence not found'}
              On failure, if closing fence is not found after an opening fence:
                {'status': 'error', 'message': 'Closing fence not found', 'opening_line_num': int}
    """
    # current_buffer = vim.current.buffer # Now passed as buffer_obj
    cursor_row, _ = vim.current.window.cursor  # cursor_row is 1-indexed

    opening_fence_line_num = 0
    opening_fence_idx = -1

    # 1. Find the opening fence (searching upwards)
    # buffer_obj is 0-indexed, so cursor_row - 1 is the current line's index in the buffer.
    for i in range(cursor_row - 1, -1, -1):
        if i >= len(buffer_obj): # Check against the length of the passed buffer_obj
            continue
        line_content = buffer_obj[i]
        if line_content.startswith("```"):
            opening_fence_line_num = i + 1 # Convert 0-indexed buffer line to 1-indexed Vim line number
            opening_fence_idx = i
            break
    
    if opening_fence_line_num == 0:
        vim.command("echom 'Python: Opening fence not found above cursor.'")
        return {'status': 'error', 'message': 'Opening fence not found'}

    # 2. Find the closing fence (searching downwards from after the opening fence)
    closing_fence_line_num = 0
    closing_fence_idx = -1
    
    # Start searching from the line *after* the opening fence, up to the end of buffer_obj
    for j in range(opening_fence_idx + 1, len(buffer_obj)):
        line_content = buffer_obj[j]
        if line_content.startswith("```"):
            closing_fence_line_num = j + 1 # Convert 0-indexed buffer line to 1-indexed
            closing_fence_idx = j
            break
    
    if closing_fence_line_num == 0:
        vim.command("echom 'Python: Closing fence not found below opening fence.'")
        return {
            'status': 'error',
            'message': 'Closing fence not found',
            'opening_line_num': opening_fence_line_num # Provide context
        }

    return {
        'status': 'success',
        'opening_line_num': opening_fence_line_num,
        'closing_line_num': closing_fence_line_num,
        'opening_fence_idx': opening_fence_idx,
        'closing_fence_idx': closing_fence_idx
    }

# Helper function to extract text between specified lines from the buffer
def _extract_text_from_buffer_lines(buffer_obj, opening_idx, closing_idx):
    """
    Extracts lines from a Vim buffer object between specified indices.

    The lines between `opening_idx` (exclusive) and `closing_idx` (exclusive)
    are extracted and joined with newline characters.

    Args:
        buffer_obj: The Vim buffer object from which to extract text.
        opening_idx (int): The 0-indexed buffer line index of the opening fence.
        closing_idx (int): The 0-indexed buffer line index of the closing fence.

    Returns:
        str: The extracted content as a single string. If no lines are between
             the fences (e.g., empty block or invalid range), an empty string is returned.
    """
    # Content is between opening_fence_idx + 1 and closing_fence_idx - 1
    # The slice buffer_obj[opening_idx + 1 : closing_idx] correctly captures these lines.
    if opening_idx + 1 >= closing_idx: # Handles empty block or invalid range
        content_lines = []
    else:
        content_lines = buffer_obj[opening_idx + 1 : closing_idx]
    
    return "\n".join(content_lines)

# Helper function to save text to a file
def _save_text_to_file(text_content, directory, filename):
    """
    Saves the given text content to a file in the specified directory.

    If the directory does not exist, it will be created.

    Args:
        text_content (str): The text content to be saved.
        directory (str): The directory where the file will be saved.
        filename (str): The name of the file.

    Returns:
        dict: {'status': 'success'} if the file was saved successfully.
              {'status': 'error', 'message': str} if an IOError occurred during saving.
    """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, filename), 'w') as f:
            f.write(text_content)
        vim.command(f"echom 'Python: Content successfully saved to {filename}'")
        return {'status': 'success'}
    except IOError as e:
        error_message = str(e).replace("'", "''") # Escape for Vim's echom
        vim.command(
            f"echohl ErrorMsg | echom 'Python: Error writing to file {filename}: {error_message}' | echohl None")
        return {'status': 'error', 'message': f'Failed to write to file: {str(e)}'}

