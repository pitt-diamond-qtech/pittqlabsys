# ADbasic Best Practices

## Event Section - Critical Rules

### ❌ NEVER use `End` in Event section
```adbasic
Event:
  Par_25 = Par_25 + 1
  Par_72 = Par_72 + 10
End  # ← This terminates the process after one execution!
```

### ✅ Correct Event section structure
```adbasic
Event:
  Par_25 = Par_25 + 1
  Par_72 = Par_72 + 10
  ' No End statement - let it return naturally
```

## Key Points

1. **Event sections run continuously** at the Processdelay rate
2. **`End` statement terminates the process** after first execution
3. **Process status drops to 0** when Event section ends with `End`
4. **Event section should return naturally** without explicit termination
5. **This affects all real-time ADbasic processes**

## Header Formatting

- **No inline comments** in header section
- **Clean parameter assignments** only
- **Strict formatting** required for proper compilation

## Example Working Structure

```adbasic
'<ADbasic Header, Headerversion 001.001>
' Process_Number         = 1
' Initial_Processdelay   = 300000
' Eventsource            = Timer
' Priority               = Normal
' ADbasic_Version        = 6.3.0
'<Header End>

#Include ADwinGoldII.inc

Init:
  Par_25 = 0
  Par_80 = 4242

Event:
  Par_25 = Par_25 + 1
  ' No End statement here!

Finish:
  Par_25 = 0
  Par_80 = 0
  Exit
```
