# Calculate the duration in seconds
end_time = datetime.now()
elapsed = (end_time - st.session_state.start_time).total_seconds() # <--- NEW: CALC DURATION

# Add 'Duration' to your 'res' dictionary for the CSV
res = {
    "Timestamp": [end_time], 
    "Class": [st.session_state.class_code], 
    "Student": [st.session_state.student_id], 
    "Topic": [st.session_state.active_topic],
    "Pre_Score": [s_pre], 
    "Post_Score": [s_post], 
    "Lift": [s_post - s_pre], 
    "NPS": [nps],
    "Duration_Sec": [int(elapsed)] # <--- NEW: SAVE SECONDS
}
