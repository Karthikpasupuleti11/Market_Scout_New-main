import React from "react";
import { RefreshCw } from "lucide-react";
import "./SectionHeader.css";
export default function SectionHeader({
  icon: Icon,
  title,
  subtitle,
  onRefresh,
  loading = false,
  children,
}) {
  return (
    <div className="page-header">
      <div className="page-header-left">
        {Icon && (
          <div className="page-header-icon">
            <Icon size={20} />
          </div>
        )}

        <div className="page-header-content">
          <h2>{title}</h2>

          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>

      <div className="page-header-actions">
        {children}

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="refresh-btn"
          >
            <RefreshCw
              size={16}
              className={loading ? "spin" : ""}
            />

            <span>
              {loading ? "Refreshing..." : "Refresh"}
            </span>
          </button>
        )}
      </div>
    </div>
  );
}   