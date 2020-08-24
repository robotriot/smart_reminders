import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";

function loadCSS(url) {
  const link = document.createElement("link");
  link.type = "text/css";
  link.rel = "stylesheet";
  link.href = url;
  document.head.appendChild(link);
}

loadCSS("https://fonts.googleapis.com/css?family=Alata");

class SmartRemindersCard extends LitElement {
  constructor() {
    super();
    this.formData = {};
    this.repeatable = false;
  }

  static get properties() {
    return {
      hass: {},
      config: {},
      formData: {},
      repeatable: false,
    };
  }

  render() {
    const reminders = Object.keys(this.hass.states)
      .filter((key) => key.includes("smart_reminders."))
      .map((key) => this.hass.states[key]);

    return html`
      <div class="smart-reminders" @keypress=${this._handle_form_submit}>
        <h2>Reminders</h2>
        <div class="reminder-add-section">
          <div class="row entry-inputs">
            <input
              type="text"
              placeholder="Add a reminder"
              name="title"
              @change=${this._handle_form_update}
            />
            <input
              type="datetime-local"
              class="date"
              name="due_date"
              @change=${this._handle_form_update}
            />
          </div>
          <div class="row repeat-section">
            <span class="is-repeatable">
              <input
                type="checkbox"
                name="repeatable"
                id="repeat-opt"
                @change=${this._handle_toggle_repeatable}
              />
              <label for="repeat-opt">Repeatable?</label>
            </span>
            ${this.repeatable
              ? html`
                  <span>
                    <span>Repeat every:</span>
                    <span>
                      <select
                        name="repeat-number"
                        id="repeat-number"
                        defaultValue="1"
                      >
                        ${Array(30)
                          .fill(1)
                          .map(
                            (i, k) =>
                              html`
                                <option value=${k + 1}>${k + 1}</option>
                              `
                          )}
                      </select>
                      <select
                        name="repeat-type"
                        id="repeat-type"
                        defaultValue="days"
                      >
                        <option value="days">days</option>
                        <option value="weeks">weeks</option>
                        <option value="months">months</option>
                      </select>
                    </span>
                  </span>
                `
              : ""}
          </div>
        </div>
        <div>
          <ul>
            ${reminders.map(
              (item) =>
                html`
                  <li class="line-item row">
                    <div>
                      <div class="title">
                        <input
                          type="checkbox"
                          class="check"
                          id=${item.entity_id}
                          .checked=${item.attributes.completed}
                          @change=${this._handle_completed}
                        />
                        <label for=${item.entity_id}
                          >${item.attributes.user} -
                          ${item.attributes.title}</label
                        >
                      </div>
                      <div
                        class=${item.state === "True"
                          ? "overdue due-date"
                          : "due-date"}
                      >
                        ${new Date(item.attributes.due).toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <button
                        class="delete-btn"
                        data-ent-id=${item.entity_id}
                        @click=${this._delete_reminder}
                      >
                        x
                      </button>
                    </div>
                  </li>
                `
            )}
          </ul>
        </div>
      </div>
    `;
  }

  setConfig(config) {
    this.config = config;
  }

  // The height of your card. Home Assistant uses this to automatically
  // distribute all cards over the available columns.
  getCardSize() {
    return 1;
  }

  _delete_reminder(e) {
    this.hass.callService("smart_reminders", "delete_task", {
      id: e.target.dataset.entId,
    });
  }

  _handle_toggle_repeatable(e) {
    this.repeatable = !this.repeatable;
  }

  _handle_completed(e) {
    this.hass.callService("smart_reminders", "complete_task", {
      id: e.target.id,
    });
  }

  _handle_form_submit(e) {
    if (e.keyCode === 13 && this.formData.title && this.formData.due_date) {
      const DOM_ROOT = this.shadowRoot;
      const repeat_type = this.repeatable
        ? DOM_ROOT.getElementById("repeat-type").value
        : "";
      const repeat_number = this.repeatable
        ? DOM_ROOT.getElementById("repeat-number").value
        : 0;
      const data = {
        ...this.formData,
        repeat_number,
        repeat_type,
        user: this.hass.user.name,
        repeatable: this.repeatable,
      };

      console.log("~~~~SUBMITTING SMART REMINDER BEEP BOOP~~~~", data);
      this.hass.callService("smart_reminders", "add_task", data);
    }
  }

  _handle_form_update(e) {
    this.formData[e.target.name] = e.target.value;
  }

  static get styles() {
    return css`
      :host {
        font-family: "Alata", sans-serif;
        font-size: 12px;
        background-color: #66999b;
        color: #fff;
        padding: 16px;
      }
      .entry-inputs,
      .line-item,
      select {
        font-size: 12px;
        font-family: "Alata", sans-serif;
      }
      .reminder-add-section {
        border-bottom: 1px solid #ffc482;
        padding-bottom: 10px;
        margin-bottom: 10px;
        background: rgb(73 106 129 / 47%);
      }
      .repeat-section {
        padding: 0 4px;
      }
      .row {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
      }
      .is-repeatable {
        flex-grow: 1;
      }
      .title {
        font-size: 12px;
      }
      .due-date {
        font-size: 10px;
        margin-top: -5px;
        padding-left: 17px;
      }
      .delete-btn {
        border: none;
        background: #ffc482;
        color: #fff;
        font-family: "Alata", sans-serif;
        line-height: 0;
        margin: 0;
        padding: 8px 8px 12px 8px;
        font-size: 12px;
        cursor: pointer;
      }
      select {
        background: transparent;
        color: white;
        border: none;
      }
      ul {
        padding: 0;
        margin: 0;
        list-style-type: none;
      }
      .title {
        flex-grow: 1;
      }
      .entry-inputs input {
        background: transparent;
        color: #fff;
        border: none;
        outline: 0;
        width: 100%;
        padding: 8px;
      }
      input[type="checkbox"] {
        margin: 0;
        vertical-align: middle;
      }
      input::placeholder {
        color: #b3af8f;
      }
      label {
        vertical-align: middle;
      }
      .overdue {
        color: red;
      }
    `;
  }
}
customElements.define("smart-reminders", SmartRemindersCard);
