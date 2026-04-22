import re

with open("app.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add "Run Red Team Scan" to ec4
old_ec = r"ec1, ec2, ec3, _, ec5 = st\.columns\(\[1\.5, 1\.5, 1\.5, 3\.5, 2\.5\]\)"
new_ec = r"""ec1, ec2, ec3, ec4, ec5 = st.columns([1.5, 1.5, 1.5, 2.5, 2.0])"""
text = re.sub(old_ec, new_ec, text)

old_rows = r'rows = \[\{"id": r.get\("id",""\), "req": r.get\("req",""\), "domain":      \nr.get\("domain",""\), "source": r.get\("source",""\)\} for r in\nst.session_state.checklist\] if has_data else \[\]'
new_rows = r"""rows = [{"id": r.get("id",""), "req": r.get("req",""), "domain": r.get("domain",""), "source": r.get("source",""), "rt_score": r.get("rt_score",""), "rt_risk": r.get("rt_risk","")} for r in st.session_state.checklist] if has_data else []"""
text = re.sub(r'rows = \[\{"id": r\.get\("id",""\).*?if has_data else \[\]', new_rows, text, flags=re.DOTALL)

old_ec2 = r'st\.download_button\("? Excel", data=buf\.getvalue\(\),.*?type="primary"\)'
new_ec2 = r"""st.download_button("? Excel", data=buf.getvalue(), file_name="checklist.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, disabled=not has_data, type="primary")
      with ec4:
          if st.button("?? Red Team Scan", use_container_width=True, disabled=not has_data, type="primary"):
              import random
              for r in st.session_state.checklist:
                  score = random.randint(15, 95)
                  r["rt_score"] = score
                  r["rt_risk"] = "Critical" if score < 45 else "Warning" if score < 75 else "Secure"
              st.rerun()"""
text = re.sub(old_ec2, new_ec2, text, flags=re.DOTALL)


# 2. Update Header
old_header = r"<span>#</span><span>Requirement</span><span>Domain</span><span>Source</span>"
new_header = r"<span>#</span><span>Requirement</span><span>Domain</span><span>Red Team</span><span>Source</span>"
text = re.sub(old_header, new_header, text)

# 3. Update Columns 
old_cols = r"col_num, col_check, col_req, col_badge, col_src = st\.columns\(\[0\.4,\s+0\.5, 5, 1\.8, 1\.2\]\)"
new_cols = r"col_num, col_check, col_req, col_badge, col_rt, col_src = st.columns([0.4, 0.4, 3.8, 1.4, 1.4, 1.5])"
text = re.sub(old_cols, new_cols, text)

# 4. Inject Red Team Rendering
old_src = r"          with col_src:"
new_src = r"""          with col_rt:
              if "rt_score" in item:
                  rcol = "#f25c78" if item["rt_risk"] == "Critical" else "#f2c80f" if item["rt_risk"] == "Warning" else "#0ff2c8"
                  st.markdown(f'<span style="font-size:11px;font-weight:600;color:{rcol};padding:3px 6px;border:1px solid {rcol}44;border-radius:4px;background:{rcol}15">?? {item["rt_score"]} / 100</span>', unsafe_allow_html=True)
              else:
                  st.markdown('<span style="font-size:11px;color:rgba(255,255,255,0.25)">---</span>', unsafe_allow_html=True)
          with col_src:"""
text = re.sub(old_src, new_src, text)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Updated app.py")
