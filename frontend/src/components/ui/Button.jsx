import { motion } from 'framer-motion'

export default function Button({ variant = 'primary', disabled, children, className = '', ...rest }) {
  return (
    <motion.button
      type="button"
      className={`btn btn-${variant} ${className}`}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      {...rest}
    >
      {children}
    </motion.button>
  )
}
