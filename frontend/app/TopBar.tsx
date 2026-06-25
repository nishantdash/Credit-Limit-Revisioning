import { Icon } from "../components/Icon";

export function TopBar() {
  return (
    <div className="topbar">
      <div className="org">
        <div className="org-mark">H</div>
        <div className="org-meta">
          <div className="org-name">Hyperface CLR <span style={{ marginLeft: 4, color: "var(--text-dim)" }}><Icon name="chevron-down" size={12} /></span></div>
          <div className="org-sub">Credit Limit Revisioning · YES Bank</div>
        </div>
      </div>
      <div className="search">
        <Icon name="search" size={14} />
        <input placeholder="Search customers, decisions..." />
        <span className="kbd">⌘K</span>
      </div>
      <div className="right">
        <button className="icon-btn" aria-label="Notifications">
          <Icon name="bell" size={18} />
          <span className="dot" />
        </button>
        <div className="user">
          <div className="av">ND</div>
          <div className="user-meta">
            <div className="user-name">Nishant Dash</div>
            <div className="user-role">Product Manager</div>
          </div>
          <Icon name="chevron-down" size={12} />
        </div>
      </div>
    </div>
  );
}
