package id.remotehp.mobile.ui

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView

object UiKit {
    const val COLOR_BACKGROUND = "#F4F6F8"
    const val COLOR_SURFACE = "#FFFFFF"
    const val COLOR_TEXT = "#121820"
    const val COLOR_MUTED = "#657180"
    const val COLOR_PRIMARY = "#1565C0"
    const val COLOR_SUCCESS = "#1B7F4A"
    const val COLOR_WARNING = "#A05A00"
    const val COLOR_ERROR = "#B3261E"
    const val COLOR_BORDER = "#DCE2E8"

    fun dp(context: Context, value: Int): Int =
        (value * context.resources.displayMetrics.density).toInt()

    fun vertical(context: Context): LinearLayout = LinearLayout(context).apply {
        orientation = LinearLayout.VERTICAL
    }

    fun title(context: Context, text: String, sizeSp: Float = 26f): TextView = TextView(context).apply {
        this.text = text
        textSize = sizeSp
        setTextColor(Color.parseColor(COLOR_TEXT))
        setTypeface(typeface, Typeface.BOLD)
    }

    fun body(context: Context, text: String = "", sizeSp: Float = 14f): TextView = TextView(context).apply {
        this.text = text
        textSize = sizeSp
        setTextColor(Color.parseColor(COLOR_MUTED))
        setLineSpacing(0f, 1.12f)
    }

    fun label(context: Context, text: String): TextView = TextView(context).apply {
        this.text = text
        textSize = 12f
        setTextColor(Color.parseColor(COLOR_MUTED))
        setTypeface(typeface, Typeface.BOLD)
        setAllCaps(true)
        letterSpacing = 0.06f
        setPadding(0, dp(context, 10), 0, dp(context, 6))
    }

    fun field(context: Context, hint: String, inputType: Int = InputType.TYPE_CLASS_TEXT): EditText =
        EditText(context).apply {
            this.hint = hint
            this.inputType = inputType
            textSize = 15f
            setTextColor(Color.parseColor(COLOR_TEXT))
            setHintTextColor(Color.parseColor("#8A94A0"))
            background = rounded(COLOR_SURFACE, COLOR_BORDER, 12f, context)
            setPadding(dp(context, 14), dp(context, 12), dp(context, 14), dp(context, 12))
            minHeight = dp(context, 50)
            setSingleLine(true)
        }

    fun primaryButton(context: Context, text: String): Button = Button(context).apply {
        this.text = text
        setAllCaps(false)
        textSize = 15f
        setTypeface(typeface, Typeface.BOLD)
        setTextColor(Color.WHITE)
        background = rounded(COLOR_PRIMARY, null, 14f, context)
        minHeight = dp(context, 52)
        setPadding(dp(context, 18), 0, dp(context, 18), 0)
    }

    fun secondaryButton(context: Context, text: String): Button = Button(context).apply {
        this.text = text
        setAllCaps(false)
        textSize = 14f
        setTypeface(typeface, Typeface.BOLD)
        setTextColor(Color.parseColor(COLOR_TEXT))
        background = rounded(COLOR_SURFACE, COLOR_BORDER, 12f, context)
        minHeight = dp(context, 48)
    }

    fun card(context: Context): LinearLayout = vertical(context).apply {
        background = rounded(COLOR_SURFACE, COLOR_BORDER, 18f, context)
        setPadding(dp(context, 18), dp(context, 18), dp(context, 18), dp(context, 18))
        elevation = dp(context, 1).toFloat()
    }

    fun statusChip(context: Context): TextView = TextView(context).apply {
        textSize = 12f
        setTypeface(typeface, Typeface.BOLD)
        setPadding(dp(context, 10), dp(context, 6), dp(context, 10), dp(context, 6))
        gravity = Gravity.CENTER
    }

    fun setStatus(chip: TextView, text: String, tone: String) {
        val (foreground, background) = when (tone) {
            "success" -> COLOR_SUCCESS to "#E8F5EE"
            "warning" -> COLOR_WARNING to "#FFF4DF"
            "error" -> COLOR_ERROR to "#FDECEA"
            else -> COLOR_MUTED to "#EDF1F4"
        }
        chip.text = text
        chip.setTextColor(Color.parseColor(foreground))
        chip.background = rounded(background, null, 999f, chip.context)
    }

    fun setLoading(button: Button, loading: Boolean, normalText: String, loadingText: String) {
        button.isEnabled = !loading
        button.alpha = if (loading) 0.65f else 1f
        button.text = if (loading) loadingText else normalText
    }

    fun <T> bindSpinner(spinner: Spinner, values: List<T>, placeholder: String) {
        val labels = if (values.isEmpty()) listOf(placeholder) else values.map { it.toString() }
        val adapter = ArrayAdapter(spinner.context, android.R.layout.simple_spinner_item, labels).apply {
            setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        }
        spinner.adapter = adapter
        spinner.isEnabled = values.isNotEmpty()
        spinner.alpha = if (values.isEmpty()) 0.55f else 1f
    }

    fun spacer(context: Context, heightDp: Int): View = View(context).apply {
        layoutParams = LinearLayout.LayoutParams(1, dp(context, heightDp))
    }

    fun fullWidth(view: View, topDp: Int = 0): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(view.context, topDp)
        }

    fun rounded(
        fill: String,
        stroke: String?,
        radiusDp: Float,
        context: Context,
    ): GradientDrawable = GradientDrawable().apply {
        shape = GradientDrawable.RECTANGLE
        setColor(Color.parseColor(fill))
        cornerRadius = dp(context, radiusDp.toInt()).toFloat()
        if (stroke != null) setStroke(dp(context, 1), Color.parseColor(stroke))
    }
}
